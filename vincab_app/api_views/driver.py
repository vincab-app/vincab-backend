from .common_imports import *
from .helper import *
from .payments import *

PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")


# api to get all driver payments
@api_view(['GET'])
@verify_firebase_token
def get_driver_payments(request, driver_id):
    user = User.objects.get(id=driver_id)
    driver = Driver.objects.get(user=user)
    driver_payments = DriverPayment.objects.filter(driver=driver)
    payments = Payment.objects.filter(ride__driver=driver)
    results = []
    for dp in payments:
        results.append({
            "driver_payment_id": dp.id,
            "driver_share": float(dp.total_amount - dp.amount),   # 90%
            "method":dp.method,
            "created_at": dp.paid_at,
            "transaction_reference": dp.transaction_reference,
            "payment_status": dp.status,
            "ride_id": dp.ride.id,
            "platform_cut": float(dp.amount),  # 10%
        })

    return JsonResponse(results, safe=False)


# api to get requested rides
@api_view(['GET'])
@verify_firebase_token
def get_requested_rides(request, user_id):
    try:
        # Get driver using user_id
        driver = Driver.objects.get(user_id=user_id)
        # print(driver.user.full_name)
    except Driver.DoesNotExist:
        return JsonResponse([], safe=False)

    rides = Ride.objects.filter(driver=driver).exclude(status__in=["completed", "cancelled"])
    # rides = Ride.objects.filter(driver=driver, status="pending")
    # print(rides)

    ride_list = []
    for ride in rides:
        ride_list.append({
            "id": ride.id,
            "pickup_lat": ride.pickup_lat,
            "pickup_lng": ride.pickup_lng,
            "dropoff_lat": ride.dropoff_lat,
            "dropoff_lng": ride.dropoff_lng,
            "distance_km": ride.distance_km,
            "estimated_fare": ride.estimated_fare,
            "status": ride.status,
            "requested_at": ride.requested_at,
            "rider_id": ride.rider.id if ride.rider else None,
            "rider_name": ride.rider.full_name if ride.rider else None,
            "rider_phone": ride.rider.phone_number if ride.rider else None,
            "pickup_address": reverse_geocode(ride.pickup_lat, ride.pickup_lng),
            "dropoff_address": reverse_geocode(ride.dropoff_lat, ride.dropoff_lng),
        })

    return JsonResponse(ride_list, safe=False)
# end of get requested rides api

# api to get driver total earnings
@api_view(['GET'])
@verify_firebase_token
def get_driver_total_earnings(request, user_id):
    try:
        # Get driver by linked user_id
        driver = Driver.objects.get(user__id=user_id)
    except Driver.DoesNotExist:
        return JsonResponse({"error": "Driver not found"}, status=404)

    # Calculate total earnings (sum of driver payments)
    total_earnings = DriverPayment.objects.filter(driver=driver).aggregate(
        total=Sum("amount")
    )["total"] or 0

    return JsonResponse({
        "driver_id": driver.id,
        "driver_name": driver.user.full_name,
        "total_earnings": float(total_earnings)  # Decimal → float
    })


# driver confirmation
@api_view(["POST"])
@verify_firebase_token
def confirm_ride(request):
    accepted = request.data.get("accepted")
    amount = request.data.get("amount")
    email = request.data.get("email")
    transaction_reference = request.data.get("transaction_reference")
    rider_id = request.data.get("rider_id")
    driver_id = request.data.get("driver_id")
    pickup_lat = request.data.get("pickup_lat")
    pickup_lng = request.data.get("pickup_lng")
    dropoff_lat = request.data.get("dropoff_lat")
    dropoff_lng = request.data.get("dropoff_lng")
    distance_km = request.data.get("distance_km")
    estimated_fare = request.data.get("estimated_fare")
    phone_number = request.data.get("phone_number")
    method = request.data.get("method")

    print("Payment method", method)

    try:
        rider = User.objects.get(id=rider_id)

        # ❌ Ride declined
        if not accepted:
            send_push_notification(
                rider.expo_token,
                "Ride Cancelled",
                "The driver declined your ride request.",
                {}
            )
            return Response({"message": "Ride declined"}, status=200)

        # ✅ MPESA PAYMENT
        if method == "mpesa":
            mpesa_response = lipa_na_mpesa(phone_number, amount)
            print("MPESA RESPONSE:", mpesa_response)

            # ✅ SUCCESS
            if mpesa_response.get("ResponseCode") == "0":

                platform_cut = float(amount) * 0.1
                driver_share = float(amount) * 0.9

                ride = Ride.objects.create(
                    rider_id=rider_id,
                    driver_id=driver_id,
                    pickup_lat=pickup_lat,
                    pickup_lng=pickup_lng,
                    dropoff_lat=dropoff_lat,
                    dropoff_lng=dropoff_lng,
                    distance_km=distance_km,
                    estimated_fare=estimated_fare,
                    status="pending",
                )

                payment = Payment.objects.create(
                    ride=ride,
                    amount=platform_cut,
                    method="mpesa",
                    status="pending",
                    transaction_reference=transaction_reference,
                    checkout_request_id=mpesa_response.get("CheckoutRequestID"),
                    merchant_request_id=mpesa_response.get("MerchantRequestID"),
                    receipt_number="",
                )

                # DriverPayment.objects.create(
                #     driver_id=driver_id,
                #     payment=payment,
                #     amount=driver_share
                # )

                send_push_notification(
                    rider.expo_token,
                    "Ride Accepted",
                    f"M-Pesa payment prompt sent to {phone_number}",
                    {
                        "ride_id": ride.id,
                        "type": "mpesa"
                    }
                )

                return Response({
                    "success": True,
                    "payment": "initiated",
                    "ride_id": ride.id,
                    "mpesa": mpesa_response
                }, status=200)

            # ❌ MPESA FAILED
            send_push_notification(
                rider.expo_token,
                "Payment Failed",
                "M-Pesa request could not be initiated.",
                {}
            )

            return Response({
                "success": False,
                "error": "MPESA_INIT_FAILED",
                "mpesa_response": mpesa_response
            }, status=400)
        
        elif method == "paystack":
            # PAYSTACK PAYMENT
            payload = {
                "email": email,
                "amount": int(float(amount) * 100),
                "reference": transaction_reference,
                "callback_url": "https://vincab-backend.onrender.com/payment_callback/",
                "metadata": {
                    "rider_id": rider_id,
                    "driver_id": driver_id,
                    "pickup_lat": pickup_lat,
                    "pickup_lng": pickup_lng,
                    "dropoff_lat": dropoff_lat,
                    "dropoff_lng": dropoff_lng,
                    "distance_km": distance_km,
                    "estimated_fare": estimated_fare,
                    "phone_number": phone_number,
                    "method": method
                }
            }

            headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
            res = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
            data = res.json()

            checkout_url = data["data"]["authorization_url"]
            reference = data["data"]["reference"]

            send_push_notification(
                rider.expo_token,
                "Ride Accepted",
                f"Pay KES {amount} to start the ride",
                {
                    "type": "payment_url",
                    "authorization_url": checkout_url,
                    "transaction_reference": reference
                }
            )

            return Response(data, status=200)

    except User.DoesNotExist:
        return Response({"error": "Rider not found"}, status=404)

    except Exception as e:
        print("ERROR:", str(e))
        return Response({"error": "Server error", "details": str(e)}, status=500)


# api to withdraw money for member
@api_view(['POST'])
@verify_firebase_token
def withdraw_money(request):
    if request.method == 'POST':
        try:
            data = request.data
            member_id = data.get("member_id")
            chama_id = data.get("chama_id")
            amount = data.get("amount") 
            withdraw_type = data.get("withdraw_type")
            chama = Chamas.objects.get(chama_id=chama_id)
            member = Members.objects.filter(chama=chama,member_id=member_id).first()

            withdrawal_result = send_mpesa_payout(member.phone_number, member.name, amount, "Savings Withdrawal")
            if not withdrawal_result["success"]:
                return Response({
                    "message": f"Withdraw failed during M-Pesa payout: {withdrawal_result.get('error')}",
                    "status": 400
                })
            withdrawal = Withdrawal(member=member, chama=chama, amount=amount, withdraw_type=withdraw_type, transactionRef=withdrawal_result["transfer_code"])
            withdrawal.save()

            Notification.objects.create(
                member=member,
                chama=chama,
                notification_type="alert",
                notification=f"You have successfully withdrawn KES.{amount}."
            )

            return JsonResponse({"message":f"Withdrawal of KES.{amount} was successful", "status": 200})

        
        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"message": "Withdraw failed", "error": str(e)}, status=500)



# end of withdrawing api

# api to check if driver is verified
def check_driver_verified(request, user_id):
    driver = get_object_or_404(Driver, user__id=user_id)
    return JsonResponse({
        "driver_id": driver.id,
        "full_name": driver.user.full_name,
        "license_number": driver.license_number,
        "verified": driver.verified,
        "rating": float(driver.rating),
        "status": driver.status
    }, status=200)


# api to update ride request status
import requests
from decimal import Decimal

@csrf_exempt
@api_view(['POST'])
def update_ride_status(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        status = data.get("status")
        ride_id = data.get("ride_id")
        rider_id = data.get("rider_id")

        ride = Ride.objects.select_related("driver").get(id=ride_id)
        ride.status = status
        ride.save()

        rider = User.objects.get(id=rider_id)

        driver = getattr(ride, "driver", None)

        # ✅ DRIVER STATUS HANDLING ONLY (NO PAYOUT)
        if driver:
            if status.lower() == "completed":
                driver.status = "active"

                message = "Ride completed successfully."
                send_push_notification(
                    driver.user.expo_token,
                    "Ride Completed",
                    message,
                    {"ride_id": ride.id}
                )

                Notification.objects.create(
                    user=driver.user,
                    message=message,
                    is_read=False
                )

            elif status.lower() == "canceled":
                driver.status = "active"

            elif status.lower() == "in_progress":
                driver.status = "busy"

            driver.save()

        # ✅ RIDER NOTIFICATION
        send_push_notification(
            rider.expo_token,
            "Ride Update",
            f"Your ride is now {status.upper()}",
            {"ride_id": ride.id}
        )

        return JsonResponse({
            "message": "Ride updated successfully",
            "ride_status": ride.status
        })

    except Ride.DoesNotExist:
        return JsonResponse({"error": "Ride not found"}, status=404)

    except User.DoesNotExist:
        return JsonResponse({"error": "Rider not found"}, status=404)

    except Exception as e:
        print("ERROR:", e)
        return JsonResponse({"error": "Server error", "details": str(e)}, status=500)


# api to get driver location
@api_view(["GET"])
# @verify_firebase_token
def get_driver_location(request, driver_id):
    driver = Driver.objects.get(id=driver_id)
    if not driver.user.current_lat or not driver.user.current_lng:
        return JsonResponse({"error": "Driver location not available"}, status=400)

    return Response({
        "driver_id": driver.id,
        "latitude": driver.user.current_lat,
        "longitude": driver.user.current_lng,
    })
