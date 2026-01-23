from .common_imports import *
from .helper import *
from .auth import verify_firebase_token


# api to get ride details
@api_view(["GET"])
def get_ride_details(request, rider_id):
    try:
        # Get latest ongoing or pending ride for the rider
        ride = Ride.objects.select_related("rider", "driver__user") \
            .filter(rider_id=rider_id) \
            .exclude(status="completed") \
            .latest("requested_at")

        vehicle = ride.driver.vehicles.first() if ride.driver else None

        # 🔹 Get human-readable addresses
        pickup_address = reverse_geocode(ride.pickup_lat, ride.pickup_lng)
        dropoff_address = reverse_geocode(ride.dropoff_lat, ride.dropoff_lng)

        eta_data = None
        if vehicle:
            eta_data = get_eta(vehicle.driver.user.current_lat, vehicle.driver.user.current_lng, ride.pickup_lat, ride.pickup_lng)

        data = {
            "id": ride.id,
            "rider": {
                "id": ride.rider.id,
                "name": ride.rider.full_name,
                "email": ride.rider.email,
                "phone": ride.rider.phone_number,
            },
            "driver": {
                "id": ride.driver.id if ride.driver else None,
                "name": ride.driver.user.full_name if ride.driver else None,
                "phone": ride.driver.user.phone_number if ride.driver else None,
                "profile_image": ride.driver.user.profile_image if ride.driver else None,
                "current_lat": ride.driver.user.current_lat if ride.driver else None,
                "current_lng": ride.driver.user.current_lng if ride.driver else None,
            } if ride.driver else None,
            "vehicle": {
                "id": vehicle.id if vehicle else None,
                "plate_number": vehicle.plate_number if vehicle else None,
                "model": vehicle.model if vehicle else None,
                "car_image": vehicle.car_image if vehicle else None,
                "current_lat": vehicle.driver.user.current_lat if vehicle else None,
                "current_lng": vehicle.driver.user.current_lng if vehicle else None,
                "eta": eta_data,
            } if vehicle else None,
            "pickup": {
                "lat": ride.pickup_lat,
                "lng": ride.pickup_lng,
                "address": pickup_address
            },
            "dropoff": {
                "lat": ride.dropoff_lat,
                "lng": ride.dropoff_lng,
                "address": dropoff_address,
            },
            "distance_km": str(ride.distance_km) if ride.distance_km else None,
            "estimated_fare": str(ride.estimated_fare) if ride.estimated_fare else None,
            "status": ride.status,
            "requested_at": ride.requested_at.isoformat(),
            "completed_at": ride.completed_at.isoformat() if ride.completed_at else None,
        }

        return JsonResponse(data, status=200)

    except Ride.DoesNotExist:
        return JsonResponse({"error": "No active ride found for this rider"}, status=404)

# end

# send expo_token
@api_view(['GET'])
# @verify_firebase_token
def send_expo_token(request, user_id, expo_token):
    try:
        user = User.objects.get(id=user_id)
        user.expo_token = expo_token
        user.save()
        return JsonResponse({"message":"Token saved successfully"})

    except User.DoesNotExist:
        return JsonResponse({"message": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)


# api to get completed rides
@api_view(["GET"])
def get_completed_rides(request, rider_id):
    try:
        rider = User.objects.get(id=rider_id)

        # ✅ Get most recent completed ride
        ride = (
            Ride.objects
            .select_related("rider", "driver", "driver__user")
            .filter(rider=rider, status="completed")
            .order_by("-completed_at")
            .first()
        )

        if not ride:
            return JsonResponse(
                {"message": "No completed rides found"},
                status=404
            )

        # ✅ Get vehicle
        vehicle = ride.driver.vehicles.first() if ride.driver else None

        # ✅ Get human-readable addresses
        pickup_address = reverse_geocode(ride.pickup_lat, ride.pickup_lng)
        dropoff_address = reverse_geocode(ride.dropoff_lat, ride.dropoff_lng)

        # ✅ Check if already rated
        rating = Rating.objects.filter(ride=ride, reviewer=ride.rider).first()
        if rating:
            return JsonResponse(
                {"data": None, "message": "You have already rated this ride"},
                status=200
            )

        # ✅ ETA
        eta_data = None
        if vehicle:
            eta_data = get_eta(
                vehicle.driver.user.current_lat,
                vehicle.driver.user.current_lng,
                ride.pickup_lat,
                ride.pickup_lng
            )

        # ✅ Build response (YOUR STRUCTURE — UNCHANGED)
        data = {
            "id": ride.id,
            "rider": {
                "id": ride.rider.id,
                "name": ride.rider.full_name,
                "email": ride.rider.email,
                "phone": ride.rider.phone_number,
            },
            "driver": {
                "id": ride.driver.id if ride.driver else None,
                "name": ride.driver.user.full_name if ride.driver else None,
                "phone": ride.driver.user.phone_number if ride.driver else None,
                "profile_image": ride.driver.user.profile_image.url if ride.driver and ride.driver.user.profile_image else None,
                "current_lat": ride.driver.user.current_lat if ride.driver else None,
                "current_lng": ride.driver.user.current_lng if ride.driver else None,
            } if ride.driver else None,
            "vehicle": {
                "id": vehicle.id if vehicle else None,
                "plate_number": vehicle.plate_number if vehicle else None,
                "model": vehicle.model if vehicle else None,
                "car_image": vehicle.car_image.url if vehicle and vehicle.car_image else None,
                "current_lat": vehicle.driver.user.current_lat if vehicle else None,
                "current_lng": vehicle.driver.user.current_lng if vehicle else None,
                "eta": eta_data,
            } if vehicle else None,
            "pickup": {
                "lat": ride.pickup_lat,
                "lng": ride.pickup_lng,
                "address": pickup_address
            },
            "dropoff": {
                "lat": ride.dropoff_lat,
                "lng": ride.dropoff_lng,
                "address": dropoff_address,
            },
            "distance_km": str(ride.distance_km) if ride.distance_km else None,
            "estimated_fare": str(ride.estimated_fare) if ride.estimated_fare else None,
            "status": ride.status,
            "requested_at": ride.requested_at.isoformat(),
            "completed_at": ride.completed_at.isoformat() if ride.completed_at else None,
        }

        return JsonResponse(data, status=200)

    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

# end

# start of update rider profile api
@csrf_exempt
@api_view(['POST'])
@parser_classes([MultiPartParser])
@verify_firebase_token
def update_rider_profile(request):
    try:
        rider_id = request.data.get('rider_id')
        name = request.data.get('name')
        profile_image = request.FILES.get('profile_image', None)

        print(rider_id, name, profile_image)

        rider = User.objects.get(id=rider_id)

        # Update name if provided
        if name:
            rider.full_name = name   # adjust field if it's first_name/last_name in your model

        # Update profile image if provided
        if profile_image:
            rider.profile_image = profile_image

        rider.save()

        return JsonResponse({
            "message": "Profile updated successfully",
            "rider": {
                "id": rider.id,
                "name": rider.full_name,
                "profile_image": rider.profile_image.url if hasattr(rider.profile_image, "url") else rider.profile_image,
            }
        })

    except User.DoesNotExist:
        return JsonResponse({"message": "Rider not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)
# end of update rider profile api


# api to update user location
@api_view(['POST'])
def update_location(request):
    try:
        user_id = request.data.get("user_id")
        lat = request.data.get("lat")
        lng = request.data.get("lng")

        if not user_id or lat is None or lng is None:
            return Response(
                {"error": "user_id, lat, and lng are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the user
        user = User.objects.get(id=user_id)

        # Update location
        user.current_lat = float(lat)
        user.current_lng = float(lng)
        user.save()

        return Response(
            {
                "message": "Location updated successfully",
                "data": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "role": user.role,
                    "current_lat": user.current_lat,
                    "current_lng": user.current_lng,
                },
            },
            status=status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# end of api to update user location

# get_notification api
@api_view(['GET'])
@verify_firebase_token
def get_user_notifications(request, user_id):
    try:
        user_id = User.objects.get(id=user_id)
        notifications = Notification.objects.filter(user=user_id, is_read=False).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return JsonResponse(serializer.data, safe=False)
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Farmer not found'}, status=status.HTTP_404_NOT_FOUND)

# end of get notification api

# api to get the nearby cars
@api_view(["GET"])
@verify_firebase_token
def nearby_vehicles(request, lat, lng):
    try:
        customer_lat = float(lat)
        customer_lng = float(lng)
    except (TypeError, ValueError):
        return Response({"error": "lat and lng query params are required"}, status=400)

    customer_location = (customer_lat, customer_lng)

    # ✅ Only active + verified drivers
    drivers = Driver.objects.select_related("user").prefetch_related("vehicles").filter(
        status="active", verified=True
    )

    vehicle_data = []
    for driver in drivers:
        if not driver.user.current_lat or not driver.user.current_lng:
            continue  # skip if no location

        driver_location = (driver.user.current_lat, driver.user.current_lng)
        distance_km = geodesic(customer_location, driver_location).km
        eta_minutes = (distance_km / 40) * 60  # assume avg 40 km/h

        for vehicle in driver.vehicles.all():  # each driver may have many vehicles
            serializer = VehicleSerializer(vehicle)
            data = serializer.data

            # Add computed + driver info
            data["eta_minutes"] = round(eta_minutes, 1)
            data["distance_km"] = round(distance_km, 2)
            data["driver_id"] = driver.id
            data["driver_name"] = driver.user.full_name
            data["driver_phone"] = driver.user.phone_number
            data["driver_image"] = driver.user.profile_image.url if driver.user.profile_image else None
            data["driver_lat"] = driver.user.current_lat
            data["driver_lng"] = driver.user.current_lng

            vehicle_data.append(data)

    # Sort by ETA (nearest first)
    sorted_vehicles = sorted(vehicle_data, key=lambda x: x["eta_minutes"])

    return Response(sorted_vehicles)


# rides/views.py
@csrf_exempt
@api_view(['POST'])
def create_ride_and_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # --- Ride Data ---
            rider_id = data.get("rider_id")
            driver_id = data.get("driver_id")  # optional
            pickup_lat = data.get("pickup_lat")
            pickup_lng = data.get("pickup_lng")
            dropoff_lat = data.get("dropoff_lat")
            dropoff_lng = data.get("dropoff_lng")
            distance_km = data.get("distance_km")
            estimated_fare = data.get("estimated_fare")

            # --- Payment Data ---
            total_amount = data.get("amount")
            method = data.get("method")
            transaction_reference = data.get("transaction_reference", "")

            # 1. Validate rider
            try:
                rider = User.objects.get(id=rider_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "Rider not found"}, status=404)

            # ✅ 2. Check if rider has an incomplete ride
            existing_ride = Ride.objects.filter(
                rider=rider, 
                status__in=["pending","accepted", "ongoing"]
            ).first()

            if existing_ride:
                return JsonResponse({
                    "error": "You already have an active ride.",
                    "ride_id": existing_ride.id,
                    "status": existing_ride.status
                }, status=210)

            # 3. Driver is optional
            driver = None
            if driver_id:
                try:
                    driver = Driver.objects.get(id=driver_id)
                    driver.status = "busy"
                except Driver.DoesNotExist:
                    return JsonResponse({"error": "Driver not found"}, status=404)

            # Split amount: 20% platform, 80% driver
            platform_cut = total_amount * 0.2
            driver_share = total_amount * 0.8

            # 4. Create Ride
            ride = Ride.objects.create(
                rider=rider,
                driver=driver,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dropoff_lat=dropoff_lat,
                dropoff_lng=dropoff_lng,
                distance_km=distance_km,
                estimated_fare=estimated_fare,
                status="pending",
            )

            # 5. Create Payment for this Ride
            payment = Payment.objects.create(
                ride=ride,
                amount=platform_cut,
                method=method,
                status="success",  # assume success for now
                transaction_reference=transaction_reference,
                paid_at=timezone.now()
            )

            # Save 80% to DriverPayment
            if ride.driver:
                DriverPayment.objects.create(
                    driver=ride.driver,
                    payment=payment,
                    amount=driver_share
                )

            # 6. Create Notifications
            rider_message = f"Your ride {ride.id} has been successfully booked and paid (KES {payment.amount})."
            Notification.objects.create(user=rider, message=rider_message)

            if driver:
                driver_message = f"You have been assigned ride {ride.id}. Pickup at ({ride.pickup_lat}, {ride.pickup_lng})."
                Notification.objects.create(user=driver.user, message=driver_message)

            # 7. Response
            return JsonResponse({
                "ride": {
                    "id": ride.id,
                    "rider": ride.rider.id,
                    "driver": ride.driver.id if ride.driver else None,
                    "pickup": [ride.pickup_lat, ride.pickup_lng],
                    "dropoff": [ride.dropoff_lat, ride.dropoff_lng],
                    "distance_km": str(ride.distance_km),
                    "fare": str(ride.estimated_fare),
                    "status": ride.status,
                    "requested_at": ride.requested_at.isoformat(),
                    "completed_at": ride.completed_at.isoformat() if ride.completed_at else None
                },
                "payment": {
                    "id": payment.id,
                    "platform_cut": platform_cut,
                    "driver_share": driver_share,
                    "method": payment.method,
                    "status": payment.status,
                    "transaction_reference": payment.transaction_reference,
                    "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
                }
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

# api to get create ratings for driver
@csrf_exempt
@verify_firebase_token
def create_rating(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            ride_id = data.get("ride_id")
            reviewer_id = data.get("reviewer_id")
            reviewee_id = data.get("reviewee_id")
            rating_value = data.get("rating")
            comment = data.get("comment", "")

            print("Ride id: ", ride_id, "Reviewer id:", reviewer_id, "Reviewee id:", reviewee_id, "Rating value:", rating_value, "Comment:", comment)

            # --- Validation ---
            if not all([ride_id, reviewer_id, reviewee_id, rating_value]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            try:
                ride = Ride.objects.get(id=ride_id)
            except Ride.DoesNotExist:
                return JsonResponse({"error": "Ride not found"}, status=404)

            try:
                reviewer = User.objects.get(id=reviewer_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "Reviewer not found"}, status=404)

            try:
                reviewee = User.objects.get(id=reviewee_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "Reviewee not found"}, status=404)

            # --- Save rating ---
            rating = Rating.objects.create(
                ride=ride,
                reviewer=reviewer,
                reviewee=reviewee,
                rating=rating_value,
                comment=comment
            )

            return JsonResponse({
                "id": rating.id,
                "ride": ride.id,
                "reviewer": reviewer.full_name,
                "reviewee": reviewee.full_name,
                "rating": rating.rating,
                "comment": rating.comment,
                "created_at": rating.created_at.isoformat()
            }, status=201)

        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)


# api to ratings for driver/user
@api_view(['GET'])
@verify_firebase_token
def get_user_ratings(request, user_id):
    """
    Fetch all ratings received by a given user
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    ratings = Rating.objects.filter(reviewee=user).order_by("-created_at")
    ratings_data = [{
        "id": r.id,
        "ride": r.ride.id,
        "reviewer": r.reviewer.full_name,
        "rating": r.rating,
        "comment": r.comment,
        "created_at": r.created_at.isoformat()
    } for r in ratings]

    return JsonResponse({"reviewee": user.full_name, "ratings": ratings_data}, safe=False)


# api to create how much rider will pay for each trip
@api_view(['GET'])
def calculate_fare(request, pickup_lat, pickup_lng, drop_lat, drop_lng):

    pickup = (pickup_lat, pickup_lng)
    drop = (drop_lat, drop_lng)

    # Distance in km
    distance_km = geodesic(pickup, drop).km  

    # Fare calculation
    rate_per_km = 50  
    fare = round(distance_km * rate_per_km, 2)

    return Response({
        "pickup": pickup,
        "drop": drop,
        "distance_km": round(distance_km, 2),
        "fare": fare
    })