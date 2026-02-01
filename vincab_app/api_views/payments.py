from .common_imports import *
from .helper import *
from .auth import verify_firebase_token



# test api for notification
@csrf_exempt
def notify_driver(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            token = data.get("token")
            title = data.get("title", "Notification")
            body = data.get("body", "")
            extra_data = data.get("data", {})

            response = send_push_notification(token, title, body, extra_data)
            return JsonResponse(response, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)


# transfer money to members using paystack
def send_mpesa_payout(phone_number, name, amount_kes, reason="Payout"):
    PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    # ✅ Normalize phone number (2547XXXXXXXX)
    phone_number = phone_number.replace("+", "").strip()

    # ========== STEP 1: CREATE RECIPIENT ==========
    recipient_payload = {
        "type": "mobile_money",
        "name": name,
        "account_number": phone_number,
        "bank_code": "MPESA",
        "currency": "KES"
    }

    try:
        recipient_res = requests.post(
            "https://api.paystack.co/transferrecipient",
            json=recipient_payload,
            headers=headers,
            timeout=30
        )
        recipient_data = recipient_res.json()
    except Exception as e:
        return {"success": False, "error": f"Recipient network error: {str(e)}"}

    if not recipient_data.get("status"):
        return {
            "success": False,
            "stage": "create_recipient",
            "error": recipient_data.get("message")
        }

    recipient_code = recipient_data["data"]["recipient_code"]

    # ========== STEP 2: SEND TRANSFER ==========
    transfer_payload = {
        "source": "balance",
        "amount": int(float(amount_kes) * 100),  # ✅ Convert KES to subunit
        "recipient": recipient_code,
        "reason": reason
    }

    try:
        transfer_res = requests.post(
            "https://api.paystack.co/transfer",
            json=transfer_payload,
            headers=headers,
            timeout=30
        )
        transfer_data = transfer_res.json()
    except Exception as e:
        return {"success": False, "error": f"Transfer network error: {str(e)}"}

    if not transfer_data.get("status"):
        return {
            "success": False,
            "stage": "transfer",
            "error": transfer_data.get("message")
        }

    status = transfer_data["data"]["status"]

    return {
        "success": True,
        "message": "Payout initiated",
        "reference": transfer_data["data"]["reference"],
        "transfer_code": transfer_data["data"]["transfer_code"],
        "amount": transfer_data["data"]["amount"],
        "recipient": transfer_data["data"]["recipient"],
        "status": status,   # pending | success | failed
    }

# end of send_mpesa_payout function

@api_view(["POST"])
def payout_view(request):
    phone = request.data["phone"]
    name = request.data["name"]
    amount = request.data["amount"]

    result = send_mpesa_payout(phone, name, amount)

    return JsonResponse(result, status=200 if result.get("success") else 400)




# start of daraja payment api
import base64
import datetime

STK_PUSH_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
DARAJA_SHORTCODE = '174379'
DARAJA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
CALLBACK_URL = 'https://vincab-backend.onrender.com/mpesa_callback/'

def lipa_na_mpesa(phone_number, amount):
    # convert amount to int
    amount = int(amount)
    access_token = get_access_token()
    if not access_token:
        return {"error": "Could not get access token"}

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{DARAJA_SHORTCODE}{DARAJA_PASSKEY}{timestamp}".encode()).decode()

    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "BusinessShortCode": DARAJA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": DARAJA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "VinCab",
        "TransactionDesc": "Payment for ride"
    }
    print("SHORTCODE:", DARAJA_SHORTCODE)
    print("PASSKEY:", DARAJA_PASSKEY)
    print("TOKEN:", access_token)
    print("URL:", STK_PUSH_URL)


    response = requests.post(STK_PUSH_URL, json=payload, headers=headers)
    return response.json()
    # return JsonResponse(response.json())

# callback endpoint to handle mpesa responses
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def mpesa_callback(request):
    if request.method == "POST":
        data = json.loads(request.body)
        stk = data.get("Body", {}).get("stkCallback", {})
        result_code = stk.get("ResultCode")
        checkout_request_id = stk.get("CheckoutRequestID")
        try:
            payment = Payment.objects.get(checkout_request_id=checkout_request_id)
            if result_code == 0:
                metadata = stk.get("CallbackMetadata", {}).get("Item", [])
                meta = {i["Name"]: i.get("Value") for i in metadata}
                payment.status = "paid"
                payment.receipt_number = meta.get("MpesaReceiptNumber")
                payment.paid_at = timezone.now()
                payment.save()
            else:
                payment.status = "failed"
                payment.save()

        except Payment.DoesNotExist:
            print("Payment with CheckoutRequestID not found:", checkout_request_id)

        print(data)
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
    return JsonResponse({"error": "Invalid request"})

# b2c payment api

B2C_URL = "https://sandbox.safaricom.co.ke/mpesa/b2c/v3/paymentrequest"

B2C_SHORTCODE = "600992"     # Your shortcode (Paybill/Till)
INITIATOR_NAME = "testapi"  # From Daraja
SECURITY_CREDENTIAL = "LOdHKAcraAmSLt0ktpXPggiIoJdXXtqisq5TpkpD31HTFE9QlOSFHscHsK/jyLtJ9xX8E4ljw3S5J+Yz/IaH8irTPhnFCZik0vcConE+D2fgWXw9/4cFmOXizS2IxMXmTpLyST5+YLGNWAnwVV8VTTYu1ppQBRog6FWQ3dEUvUDOylIVy5kX9p1J6HdFOay6LLqb/7/y7LJy6n7R+6tEwWXmigwdeGueMkaOUUuujEo6T87Hw3bvpFbEx+WkY9bIKGKZNoHk9NUQWyHQleLIRISyhRlrh9WrekFGx7ONaGT/gL8HHj4RWoSCujJ/IA0EE6wWrptZc1jcWfgKtGWECg=="  # Encrypted initiator password

B2C_CALLBACK_URL = "https://vincab-backend.onrender.com/b2c_callback/"

import uuid

mpesa_originator_id = str(uuid.uuid4())


def send_b2c_payment(phone_number, amount):
    # convert amount to int
    amount = int(amount)
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "OriginatorConversationID": mpesa_originator_id,
        "InitiatorName": INITIATOR_NAME,
        "SecurityCredential": SECURITY_CREDENTIAL,
        "CommandID": "BusinessPayment",  # options: BusinessPayment, SalaryPayment, PromotionPayment
        "Amount": amount,
        "PartyA": B2C_SHORTCODE,
        "PartyB": phone_number,
        "Remarks": "Payment",
        "QueueTimeOutURL": B2C_CALLBACK_URL,
        "ResultURL": B2C_CALLBACK_URL,
        "Occasion": "Salary"
    }

    response = requests.post(B2C_URL, json=payload, headers=headers)
    return response.json()
    # return JsonResponse(response.json())

# b2c callback endpoint
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
@api_view(["POST"])
def b2c_callback(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)

        result = data.get("Result", {})
        result_code = result.get("ResultCode")
        result_desc = result.get("ResultDesc")
        originator_id = result.get("OriginatorConversationID")
        conversation_id = result.get("ConversationID")
        transaction_id = result.get("TransactionID")

        # FIND PAYMENT RECORD
        driver_payment = DriverPayment.objects.filter(
            originator_conversation_id=originator_id
        ).first()

        if not driver_payment:
            return JsonResponse({"error": "No driver payment found"}, status=404)

        # SAVE CALLBACK DATA
        driver_payment.conversation_id = conversation_id
        driver_payment.transaction_id = transaction_id

        #  HANDLE PAYOUT RESULT
        if result_code == 2040:
            driver_payment.status = "paid"

            message = f"Your payout was successful. Transaction ID: {transaction_id}"
        else:
            driver_payment.status = "failed"

            message = f"Payout failed. Reason: {result_desc}"

        driver_payment.result_code = result_code
        driver_payment.result_description = result_desc
        driver_payment.save()

        # DRIVER NOTIFICATION
        driver = driver_payment.driver
        send_push_notification(
            driver.user.expo_token,
            "Mpesa Payout Update",
            message,
            {"transaction_id": transaction_id}
        )

        # CREATE IN-APP NOTIFICATION
        Notification.objects.create(
            user=driver.user,
            message=message,
            is_read=False
        )

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Acknowledged"})

    except Exception as e:
        print("B2C CALLBACK ERROR:", e)
        return JsonResponse({"ResultCode": 1, "ResultDesc": "Server Error"})



# paystack initialize payment
PAYSTACK_SECRET_KEY = "sk_test_a60107fb70a0a8424b1ce810d3c677a4229b168e"

# initiliaze payment 2
@api_view(["POST"])
def initialize_payment(request):
    amount = request.data.get("amount")   #  you are sending this
    email = request.data.get("email", "customer@email.com")  # fallback email
    transaction_reference = request.data.get("transaction_reference")
    rider_id = request.data.get("rider_id")
    driver_id = request.data.get("driver_id")
    pickup_lat = request.data.get("pickup_lat")
    pickup_lng = request.data.get("pickup_lng")
    dropoff_lat = request.data.get("dropoff_lat")
    dropoff_lng = request.data.get("dropoff_lng")
    distance_km = request.data.get("distance_km")
    estimated_fare = request.data.get("estimated_fare")
    phone_number = request.data.get("phone_number", "N/A")
    method = request.data.get("method", "paystack")  # default to paystack

    # print all the date sent
    print("Rider Id:", rider_id, "Driver Id:", driver_id, "Amount:", amount, "Reference:", transaction_reference, "email:", email, "phonenumber:",phone_number, "method:", method)

    if not all([amount, rider_id, driver_id]):
        return Response({"error": "Missing required fields"}, status=400)

    # Check for active rides
    existing_ride = Ride.objects.filter(
        rider=rider_id, 
        status__in=["pending", "accepted", "ongoing"]
    ).first()

    if existing_ride:
        return JsonResponse({
            "error": "You already have an active ride.",
            "ride_id": existing_ride.id,
            "status": existing_ride.status
        }, status=210)

    # Send push notification to driver to confirm
    try:
        driver = Driver.objects.get(id=driver_id)
        rider = User.objects.get(id=rider_id)
        message = f"Ride request from {rider.full_name}. Amount: {amount} KES. Accept?"
        
        send_push_notification(
            driver.user.expo_token,
            "New Ride Request",
            message,
            {
                "type": "ride_request",
                "rider_id": rider_id,
                "driver_id": driver_id,
                "email": email,
                "amount": amount,
                "pickup_lat": pickup_lat,
                "pickup_lng": pickup_lng,
                "dropoff_lat": dropoff_lat,
                "dropoff_lng": dropoff_lng,
                "distance_km": distance_km,
                "estimated_fare": estimated_fare,
                "phone_number": phone_number,
                "method": method,
                "transaction_reference": transaction_reference,
            }
        )

        return JsonResponse({"message": "Ride request sent to driver for confirmation"}, status=200)

    except Exception as e:
        print(e)
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
def payment_callback(request):
    reference = request.GET.get('reference')

    if not reference:
        return JsonResponse({"error": "Missing reference"}, status=400)

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    response = requests.get(url, headers=headers).json()

    data = response.get("data")
    if not data or not isinstance(data, dict):
        return JsonResponse({"error": "Invalid Paystack response", "details": response}, status=400)

    if data.get("status") != "success":
        return JsonResponse({"status": "failed"}, status=400)

    try:
        # ✅ Handle metadata safely
        metadata = data.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}

        rider_id = metadata.get("rider_id")
        driver_id = metadata.get("driver_id")
        pickup_lat = metadata.get("pickup_lat")
        pickup_lng = metadata.get("pickup_lng")
        dropoff_lat = metadata.get("dropoff_lat")
        dropoff_lng = metadata.get("dropoff_lng")
        distance_km = metadata.get("distance_km")
        estimated_fare = metadata.get("estimated_fare")
        total_amount = data.get("amount", 0) / 100
        method = "paystack"
        transaction_reference = reference

        # --- Check if this payment already exists (idempotency) ---
        existing_payment = Payment.objects.filter(transaction_reference=transaction_reference).first()
        if existing_payment:
            return JsonResponse({"status": "already_processed"}, status=200)

        # --- Validate rider ---
        try:
            rider = User.objects.get(id=rider_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "Rider not found"}, status=404)

        # --- Optional driver ---
        driver = None
        if driver_id:
            try:
                driver = Driver.objects.get(id=driver_id)
                driver.status = "busy"
                driver.save()
            except Driver.DoesNotExist:
                return JsonResponse({"error": "Driver not found"}, status=404)

        platform_cut = total_amount * 0.1
        driver_share = total_amount * 0.9

        # ✅ Transaction ensures no duplicates if Paystack retries
        with transaction.atomic():
            # Double-check again inside transaction
            if Payment.objects.filter(transaction_reference=transaction_reference).exists():
                return JsonResponse({"status": "already_processed"}, status=200)

            # --- Create ride ---
            ride = Ride.objects.create(
                rider=rider,
                driver=driver,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dropoff_lat=dropoff_lat,
                dropoff_lng=dropoff_lng,
                distance_km=distance_km,
                estimated_fare=estimated_fare,
                status="pending"
            )

            # --- Save platform payment ---
            payment = Payment.objects.create(
                ride=ride,
                amount=platform_cut,
                method=method,
                status="paid",
                transaction_reference=transaction_reference,
                paid_at=timezone.now()
            )

            # --- Save driver share ---
            if driver:
                DriverPayment.objects.create(
                    driver=driver,
                    payment=payment,
                    amount=driver_share
                )

            # --- Notifications ---
            Notification.objects.create(
                user=rider,
                message=f"Your ride has been successfully booked and paid KES {total_amount}."
            )
            if driver:
                Notification.objects.create(
                    user=driver.user,
                    message=f"You have been assigned ride {ride.id}. Pickup at {ride.pickup_lat}, {ride.pickup_lng}."
                )
                send_push_notification(
                    driver.user.expo_token,
                    "Ride Assigned",
                    f"You have been assigned ride {ride.id}. Be sure to pick up the rider on time.",
                    {"ride_id": ride.id}
                )

        return render(request, "payment_status.html", {
            "status": "paid",
            "ride": ride,
            "payment": payment,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

