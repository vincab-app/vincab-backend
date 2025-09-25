from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import pyrebase
from .models import User, Notification, Vehicle, Ride, Payment, Driver, Rating, DriverPayment
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import NotificationSerializer, VehicleSerializer
from geopy.distance import geodesic
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
import requests
from django.db.models import Sum
from django.utils.timezone import now
from datetime import timedelta




config = {
    "apiKey": "AIzaSyA4rY0QdPta2Y_EnXlQnRMP65ooCHKmkAU",
    "authDomain": "vincab-b1fd6.firebaseapp.com",
    "databaseURL": "https://vincab-b1fd6-default-rtdb.firebaseio.com/",
    "projectId": "vincab-b1fd6",
    "storageBucket": "vincab-b1fd6.firebasestorage.app",
    "messagingSenderId": "734798694430",
   " appId": "1:734798694430:web:3eb12298a075fa15ac860f",
   " measurementId": "G-44KSWZVPDR"
}
firebase = pyrebase.initialize_app(config)
authe = firebase.auth() 
database = firebase.database()

import firebase_admin
from firebase_admin import auth, credentials
import os, json

# Initialize Firebase once (e.g., in settings.py or a startup file)
# service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
cred = credentials.Certificate("serviceAccountKey.json")
# cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

def verify_firebase_token(view_func):
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({"message": "Unauthorized"}, status=401)
        
        token = auth_header.split(" ")[1]
        try:
            decoded_token = auth.verify_id_token(token)
            # You can attach UID and email from token to the request for easy access
            request.user_uid = decoded_token.get("uid")
            request.user_email = decoded_token.get("email")
        except Exception as e:
            return JsonResponse({"message": "Invalid or expired token", "error": str(e)}, status=401)
        
        return view_func(request, *args, **kwargs)
    return wrapper



def index(request):
    return HttpResponse("Hello world!")


#start of signin api
@csrf_exempt
@api_view(['POST'])
def signin(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return JsonResponse({"message": "Email and password are required"}, status=400)

            user = authe.sign_in_with_email_and_password(email, password)
            
            if User.objects.filter(email=email).exists():
                session_id = user['idToken']
                request.session['uid'] = str(session_id)
                get_user = User.objects.filter(email=email).first()
                user_id = get_user.id
                user_name = get_user.full_name
                phone_number = get_user.phone_number
                role = get_user.role
                profile_image = get_user.profile_image
                date_joined = get_user.date_joined
                current_lat = get_user.current_lat
                current_lng = get_user.current_lng
                return JsonResponse({"message": "Successfully logged in", "token":session_id, "user_id":user_id, "user_name":user_name,"user_email":email,"phone_number":phone_number,"role":role, "current_lat":current_lat, "current_lng":current_lng, "profile_image":profile_image, "date_joined":date_joined}, status=200)
            else:
                return JsonResponse({"message": "No user found with this email, please register"}, status=404)

        except Exception as e:
            print("Error:", str(e))  # Optional logging
            return JsonResponse({"message": "Invalid credentials. Please check your email and password."}, status=401)

    return JsonResponse({"message": "Invalid request method"}, status=405)
#end of signin api


# start of signup api
@csrf_exempt
@api_view(['POST'])
def signup(request):
    if request.method == 'POST':
        try:
            data = request.data

            full_name = data.get("full_name")
            phone_number = data.get("phone_number")
            email = data.get("email")
            password = data.get("password")

            print(full_name, phone_number, email, password)

            if not all([full_name, email, password, phone_number]):
                return JsonResponse({"message": "Missing required fields"}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({"message": "Email already exists"}, status=400)

            user = authe.create_user_with_email_and_password(email, password)
            uid = user['localId']


            user = User(
                full_name=full_name,
                phone_number=phone_number,
                email=email,
                password=uid
            )
            user.save()

            notification = Notification.objects.create(
                user=user,
                message="Welcome to VinCab! Your account has been created successfully.",
                is_read=False
            )

            return JsonResponse({"message": "Successfully signed up"}, status=201)

        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"message": "Signup failed", "error": str(e)}, status=500)

    return JsonResponse({"message": "Invalid request method"}, status=405)

#end of signup api

# reset password api
@api_view(['GET'])
def reset_password(request, email):
    try:
        authe.send_password_reset_email(email)
        message = "An email to reset password is successfully sent"
        return JsonResponse({"message": message})
    except:
        message = "Something went wrong, Please check the email, provided is registered or not"
        return JsonResponse({"message": message})
#end of reset api

# semd push notification to phne
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

def send_push_notification(token, title, body, data=None):
    if not token:
        return {"error": "No push token provided."}

    message = {
        "to": f"{token}",
        "sound": "default",
        "title": f"{title}",
        "body": f"{body}",
        "data": data or {},
    }

    try:
        response = requests.post(EXPO_PUSH_URL, json=message)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


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



# get_notification api
@api_view(['GET'])
# @verify_firebase_token
def get_user_notifications(request, user_id):
    try:
        user_id = User.objects.get(id=user_id)
        notifications = Notification.objects.filter(user=user_id, is_read=False).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return JsonResponse(serializer.data, safe=False)
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Farmer not found'}, status=status.HTTP_404_NOT_FOUND)

# end of get notification api


@api_view(["GET"])
# @verify_firebase_token
def nearby_vehicles(request, lat, lng):
    try:
        customer_lat = float(lat)
        customer_lng = float(lng)
    except (TypeError, ValueError):
        return Response({"error": "lat and lng query params are required"}, status=400)

    customer_location = (customer_lat, customer_lng)

    vehicles = Vehicle.objects.select_related("driver").all()  # ✅ optimize query
    vehicle_data = []

    for v in vehicles:
        if v.current_lat is None or v.current_lng is None:
            continue

        vehicle_location = (v.current_lat, v.current_lng)
        distance_km = geodesic(customer_location, vehicle_location).km  

        # assume avg speed = 40 km/h
        eta_minutes = (distance_km / 40) * 60  

        serializer = VehicleSerializer(v)
        data = serializer.data
        data["eta_minutes"] = round(eta_minutes, 1)

        # ✅ Add driver image (check your Driver model field, e.g., profile_image)
        if v.driver.user.profile_image:
            data["driver_image"] = v.driver.user.profile_image
        else:
            data["driver_image"] = None

        if v.driver.user.full_name:
            data["driver_name"] = v.driver.user.full_name
        else:
            data["driver_name"] = None

        if v.driver.user.phone_number:
            data["driver_phone"] = v.driver.user.phone_number
        else:
            data["driver_phone"] = None

        vehicle_data.append(data)

    # Sort by ETA
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

            # 2. Driver is optional
            driver = None
            if driver_id:
                try:
                    driver = Driver.objects.get(id=driver_id)
                except Driver.DoesNotExist:
                    return JsonResponse({"error": "Driver not found"}, status=404)

            # Split amount: 20% platform, 80% driver
            platform_cut = total_amount * 0.2
            driver_share = total_amount * 0.8

            # 3. Create Ride
            ride = Ride.objects.create(
                rider=rider,
                driver=driver,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dropoff_lat=dropoff_lat,
                dropoff_lng=dropoff_lng,
                distance_km=distance_km,
                estimated_fare=estimated_fare,
                status="completed",  # mark as completed immediately after payment
                completed_at=timezone.now()
            )

            # 4. Create Payment for this Ride
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

            # 5. Create Notifications
            rider_message = f"Your ride {ride.id} has been successfully booked and paid (KES {payment.amount})."
            Notification.objects.create(user=rider, message=rider_message)

            if driver:
                driver_message = f"You have been assigned ride {ride.id}. Pickup at ({ride.pickup_lat}, {ride.pickup_lng})."
                Notification.objects.create(user=driver.user, message=driver_message)

            # 6. Response
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
def create_rating(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            ride_id = data.get("ride_id")
            reviewer_id = data.get("reviewer_id")
            reviewee_id = data.get("reviewee_id")
            rating_value = data.get("rating")
            comment = data.get("comment", "")

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
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)


# api to ratings for driver/user
@api_view(['GET'])
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


# api to get all payments for admin
@api_view(['GET'])
def get_all_payments(request):
    payments = Payment.objects.all().values(
        "id",
        "amount",
        "status",
        "method",
        "transaction_reference",
        "paid_at",
        "ride__driver__user__full_name",
        "ride__rider__full_name",
    )
    return JsonResponse(list(payments), safe=False)

# api to get all driver payments
@api_view(['GET'])
def get_driver_payments(request, driver_id):
    driver_payments = DriverPayment.objects.filter(driver_id=driver_id).select_related("payment", "payment__ride")

    results = []
    for dp in driver_payments:
        results.append({
            "driver_payment_id": dp.id,
            "driver_share": float(dp.amount),   # 80%
            "method":dp.payment.method,
            "created_at": dp.created_at,
            "transaction_reference": dp.payment.transaction_reference,
            "payment_status": dp.payment.status,
            "ride_id": dp.payment.ride.id,
            "platform_cut": float(dp.payment.amount),  # 20%
        })

    return JsonResponse(results, safe=False)


# api to get requested rides
@api_view(['GET'])
def get_requested_rides(request, user_id):

    try:
        # Get driver using user_id
        driver = Driver.objects.get(user_id=user_id)
    except Driver.DoesNotExist:
        return JsonResponse([], safe=False)  # No driver found, return empty array

    rides = Ride.objects.filter(driver=driver, status="pending").values(
        "id",
        "pickup_lat",
        "pickup_lng",
        "dropoff_lat",
        "dropoff_lng",
        "distance_km",
        "estimated_fare",
        "status",
        "requested_at",
        "rider__id",
        "rider__full_name"
    )

    return JsonResponse(list(rides), safe=False)  # If empty, it will return []



# api to update ride request status
@csrf_exempt
def update_ride_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            status = data.get("status")
            ride_id = data.get('ride_id')
            rider_id = data.get('rider_id')

            ride = Ride.objects.get(id=ride_id)
            ride.status = status
            ride.save()
            rider = User.objects.get(id=rider_id)

            extra_data = {"ride_id":ride_id}

            response = send_push_notification(rider.expo_token, "Ride Update", f"Your ride request has been updated. Status: {status}", extra_data)
            return JsonResponse(response, safe=False)

            return JsonResponse({"message": "Ride status updated", "status": ride.status})
        except Ride.DoesNotExist:
            return JsonResponse({"error": "Ride not found"}, status=404)
    return JsonResponse({"error": "Invalid request"}, status=400)

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



# api to get driver total earnings
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



# api to get vincab earnings
def get_vincab_earnings(request):
    today = now().date()

    # Daily earnings (today only, status = success)
    daily_total = Payment.objects.filter(
        paid_at__date=today, status="success"
    ).aggregate(total=Sum("amount"))["total"] or 0

    # Weekly earnings (from Monday to today, status = success)
    week_start = today - timedelta(days=today.weekday())  # Monday start
    weekly_total = Payment.objects.filter(
        paid_at__date__gte=week_start, status="success"
    ).aggregate(total=Sum("amount"))["total"] or 0

    # Monthly earnings (current month, status = success)
    monthly_total = Payment.objects.filter(
        paid_at__year=today.year, paid_at__month=today.month, status="success"
    ).aggregate(total=Sum("amount"))["total"] or 0

    return JsonResponse({
        "daily_earnings": float(daily_total),
        "weekly_earnings": float(weekly_total),
        "monthly_earnings": float(monthly_total),
        "currency": "KES"
    })


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


# 🔹 Helper: Reverse Geocoding using OpenStreetMap (Free)
def reverse_geocode(lat, lng):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        headers = {"User-Agent": "YourAppName/1.0"}  # Nominatim requires User-Agent
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        return data.get("display_name", None)
    except Exception as e:
        print("Reverse geocode error:", e)
        return None

# calculate the time btwn vehicle and rider's pick location
def get_eta(vehicle_lat, vehicle_lng, pickup_lat, pickup_lng):
    url = f"https://router.project-osrm.org/route/v1/driving/{vehicle_lng},{vehicle_lat};{pickup_lng},{pickup_lat}?overview=false"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        if data.get("routes"):
            duration_seconds = data["routes"][0]["duration"]
            distance_meters = data["routes"][0]["distance"]
            return {
                "eta_minutes": round(duration_seconds / 60, 1),
                "distance_km": round(distance_meters / 1000, 2),
            }
    return None


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
            eta_data = get_eta(vehicle.current_lat, vehicle.current_lng, ride.pickup_lat, ride.pickup_lng)

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
                "current_lat": vehicle.current_lat if vehicle else None,
                "current_lng": vehicle.current_lng if vehicle else None,
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


