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
            "pickup_address": ride.pickup_address,
            "dropoff_address": ride.dropoff_address,
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
        total=Sum("pending_amount")
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

# api to check if driver is verified
@api_view(['GET'])
@verify_firebase_token
def check_driver_verified(request, user_id):
    driver = get_object_or_404(Driver, user__id=user_id)
    vehicle = Vehicle.objects.get(driver=driver)

    return JsonResponse({
        "driver_id": driver.id,
        "full_name": driver.user.full_name,
        "license_number": driver.license_number,
        "vehicle_image": vehicle.car_image.url if hasattr(vehicle.car_image, "url") else vehicle.car_image,
        "verified": driver.verified,
        "rating": float(driver.rating),
        "status": driver.status
    }, status=200)


# api to update ride request status
@csrf_exempt
@api_view(['POST'])
@verify_firebase_token
def update_ride_status(request):

    try:
        data = json.loads(request.body)
        status = data.get("status")
        ride_id = data.get("ride_id")
        rider_id = data.get("rider_id")
        code = data.get("code")

        ride = Ride.objects.select_related("driver").get(id=ride_id)
        rider = User.objects.get(id=rider_id)
        driver = getattr(ride, "driver", None)

        driver_payment = DriverPayment.objects.get(driver=driver)

        if not driver:
            return JsonResponse({"error": "Driver not assigned"}, status=400)

        status = status.lower()

        # VERIFY CODES BEFORE UPDATING STATUS
        if status == "picked":
            if not code or str(code) != str(ride.pick_code):
                return JsonResponse(
                    {"error": "Invalid pickup code"},
                    status=400
                )

        if status == "completed":
            if not code or str(code) != str(ride.complete_code):
                return JsonResponse(
                    {"error": "Invalid completion code"},
                    status=400
                )

        # ONLY UPDATE IF VALID
        ride.status = status
        ride.save()

        # ===== STATUS LOGIC =====
        if status == "completed":
            driver.status = "active"
            send_push_notification(
                rider.expo_token,
                "Ride Completed",
                "Your ride has been completed. Thank you for riding with VinCab.",
                {"ride_id":ride.id}
            )
            Notification.objects.create(
                user=rider,
                message="Your ride has been completed. Thank you for riding with VinCab."
            )
            driver_payment.pending_amount += driver_payment.float_amount
            driver_payment.float_amount = 0.0
            driver_payment.save()

        elif status == "accepted":
            send_push_notification(
                rider.expo_token,
                "Ride Accepted",
                "Your ride has been accepted. Driver is on the way.",
                {"ride_id": ride.id}
            )

        elif status == "picked":
            send_push_notification(
                rider.expo_token,
                "Ride Started",
                "You have been picked. Enjoy your trip.",
                {"ride_id": ride.id}
            )

        elif status == "canceled":
            driver.status = "active"

        elif status == "in_progress":
            driver.status = "busy"

        driver.save()

        return JsonResponse({
            "message": "Ride updated successfully",
            "ride_status": ride.status
        })

    except Ride.DoesNotExist:
        return JsonResponse({"error": "Ride not found"}, status=404)

    except User.DoesNotExist:
        return JsonResponse({"error": "Rider not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": "Server error", "details": str(e)}, status=500)


# api to get driver location
@api_view(["GET"])
@verify_firebase_token
def get_driver_location(request, driver_id):
    driver = Driver.objects.get(id=driver_id)
    if not driver.user.current_lat or not driver.user.current_lng:
        return JsonResponse({"error": "Driver location not available"}, status=400)

    return Response({
        "driver_id": driver.id,
        "latitude": driver.user.current_lat,
        "longitude": driver.user.current_lng,
    })


# start of update driver profile api
@csrf_exempt
@api_view(['POST'])
@parser_classes([MultiPartParser])
@verify_firebase_token
def update_driver_profile(request):
    try:
        rider_id = request.data.get('rider_id')
        name = request.data.get('name')
        profile_image = request.FILES.get('profile_image', None)
        vehicle_image = request.FILES.get('vehicle_image', None)

        print(rider_id, name, profile_image, vehicle_image)

        rider = User.objects.get(id=rider_id)

        # Update name if provided
        if name:
            rider.full_name = name   # adjust field if it's first_name/last_name in your model

        # Update profile image if provided
        profile_url = None
        if profile_image:
            upload_result = cloudinary.uploader.upload(profile_image)
            profile_url = upload_result.get("secure_url")

        rider.profile_image = profile_url if profile_url else rider.profile_image
        rider.save()
        
        vehicle_url = None
        if vehicle_image:
            upload_result = cloudinary.uploader.upload(vehicle_image)
            vehicle_url = upload_result.get("secure_url")

        driver = Driver.objects.filter(user=rider).first()
        vehicle = Vehicle.objects.filter(driver=driver).first()
        if vehicle and vehicle_image:
            vehicle.car_image = vehicle_url
            vehicle.save()

        return JsonResponse({
            "message": "Profile updated successfully",
            "rider": {
                "id": rider.id,
                "name": rider.full_name,
                "profile_image": rider.profile_image,
                "vehicle_image": vehicle.car_image if vehicle else None,
            }
        })

    except User.DoesNotExist:
        print("Rider not found")
        return JsonResponse({"message": "Rider not found"}, status=404)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return JsonResponse({"message": str(e)}, status=500)
# end of update driver profile api
