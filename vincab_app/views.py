from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import pyrebase
from .models import User, Notification, Vehicle, Ride, Payment, Driver, Rating, DriverPayment
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import NotificationSerializer, VehicleSerializer, DriverSerializer, RideSerializer, PaymentSerializer, DashboardStatsSerializer
from geopy.distance import geodesic
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
import requests
from django.db.models import Sum, Q
from django.utils.timezone import now
from datetime import timedelta
import cloudinary.uploader
from decimal import Decimal
from django.utils.timezone import now
from rest_framework import status
from django.http import JsonResponse
from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view
import requests, json





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
service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
# cred = credentials.Certificate("serviceAccountKey.json")
cred = credentials.Certificate(service_account_info)
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

            # print(full_name, phone_number, email, password)

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


# start of driver signup api
@csrf_exempt
@api_view(['POST'])
def driversignup(request):
    if request.method == 'POST':
        try:
            data = request.data

            full_name = data.get("full_name")
            phone_number = data.get("phone_number")
            email = data.get("email")
            license_number = data.get("license_number")
            password = data.get("password")
            car_make = data.get("car_make")
            car_model = data.get("car_model")
            car_plate = data.get("car_plate")
            car_color = data.get("car_color")
            expo_token = data.get("expo_token")
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            car_image = request.FILES.get("car_image")

            print(full_name, phone_number, email, password, license_number, car_make, car_model, car_plate, car_color, expo_token, latitude, longitude, car_image)

            if not all([full_name, email, password, phone_number, license_number, car_make, car_model, car_plate, car_color, expo_token, car_image]):
                return JsonResponse({"message": "Missing required fields"}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({"message": "Email already exists"}, status=400)

            firebase_user = authe.create_user_with_email_and_password(email, password)
            uid = firebase_user['localId']


            user = User(
                full_name=full_name,
                phone_number=phone_number,
                email=email,
                role="driver",
                password=uid,
                current_lat=latitude,
                current_lng=longitude,
                expo_token=expo_token
            )
            user.save()

            driver = Driver(
                user=user,
                license_number=license_number,
                verified=False,
                rating=0,
                status="inactive"
            )
            driver.save()

            car_image_url = None
            if car_image:
                upload_result = cloudinary.uploader.upload(car_image)
                car_image_url = upload_result.get("secure_url")

            vehicle = Vehicle(
                driver=driver,
                plate_number=car_plate,
                model=car_model,
                vehicle_type="car",
                color=car_color,
                car_image=car_image_url
            )
            vehicle.save()

            notification = Notification.objects.create(
                user=user,
                message="Welcome to VinCab! Your account has been created successfully.",
                is_read=False
            )

            notification = Notification.objects.create(
                user=user,
                message="Your request to be a driver at VinCab was received successfully. We'll get back to you wuthin 48 hours.",
                is_read=False
            )

            return JsonResponse({"message": "Successfully signed up"}, status=201)

        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"message": "Signup failed", "error": str(e)}, status=500)

    return JsonResponse({"message": "Invalid request method"}, status=405)

#end of driver signup api



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


# 🔹 Helper: Reverse Geocoding using OpenStreetMap (Free)
def reverse_geocode(lat, lng):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        headers = {"User-Agent": "VinCab/1.0 (contact@vincab.com)"}
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        address = data.get("address", {})
        return f"{address.get('city', '')}, {address.get('country', '')}"
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
# @verify_firebase_token
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
            data["driver_image"] = driver.user.profile_image
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
    user = User.objects.get(id=driver_id)
    driver = Driver.objects.get(user=user)
    driver_payments = DriverPayment.objects.filter(driver=driver)
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




# api to update ride request status
import requests
from decimal import Decimal

@csrf_exempt
def update_ride_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            status = data.get("status")
            ride_id = data.get("ride_id")
            rider_id = data.get("rider_id")

            ride = Ride.objects.get(id=ride_id)
            ride.status = status
            ride.save()

            rider = User.objects.get(id=rider_id)

            # ✅ Handle driver availability + payout
            if ride.driver:
                driver = ride.driver  

                if status.lower() == "completed":
                    # Mark driver as active again
                    driver.status = "active"
                    driver.save()
                    driver_share = Decimal("0.8") * Decimal(str(ride.estimated_fare))

                    # --- Send payout to driver ---
                    payout_payload = {
                        "driverPhone": driver.user.phone_number,   # make sure model has phone_number
                        "amount": str(driver_share)          # adjust to your fare/amount field
                    }
                    try:
                        payout_response = requests.post(
                            "https://vincab-payment-1.onrender.com/payout/",   # your Node.js payout API
                            json=payout_payload,
                            timeout=15
                        )
                        payout_result = payout_response.json()

                        # ✅ Send push notification to driver
                        send_push_notification(
                            driver.expo_token,
                            "Payout Received",
                            f"You have been paid {ride.fare_amount} for completing the ride.",
                            {"ride_id": ride.id}
                        )

                    except Exception as payout_err:
                        print("Payout error:", payout_err)

                elif status.lower() == "canceled":
                    driver.status = "active"
                    driver.save()

                elif status.lower() == "in_progress":
                    driver.status = "busy"
                    driver.save()

            # ✅ Notify rider about ride status
            extra_data = {"ride_id": ride_id}
            send_push_notification(
                rider.expo_token,
                "Ride Update",
                f"Your ride request has been updated. Status: {status}",
                extra_data
            )

            return JsonResponse({"message": "Ride status updated", "status": ride.status})

        except Ride.DoesNotExist:
            return JsonResponse({"error": "Ride not found"}, status=404)
        except User.DoesNotExist:
            return JsonResponse({"error": "Rider not found"}, status=404)

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
            upload_result = cloudinary.uploader.upload(profile_image)
            image_url = upload_result.get("secure_url")
            rider.profile_image = image_url  # assuming your model has an ImageField or CharField

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


# admin api to get all drivers
@api_view(['GET'])
def get_all_drivers(request):
    drivers = Driver.objects.select_related("user").prefetch_related("vehicles").all()
    serializer = DriverSerializer(drivers, many=True)
    return Response(serializer.data)
# end of admin api to get all drivers


# api to get all riders
@api_view(['GET'])
def get_all_riders(request):
    try:
        riders = User.objects.filter(role="rider")
        riders_data = []

        for rider in riders:
            riders_data.append({
                "id": rider.id,
                "full_name": rider.full_name,
                "email": rider.email,
                "phone_number": rider.phone_number,
                "profile_image": rider.profile_image,
                "current_lat": rider.current_lat,
                "current_lng": rider.current_lng,
                "date_joined": rider.date_joined,
                "expo_token": rider.expo_token,
            })

        return JsonResponse({"riders": riders_data}, status=200, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
# end of api to get all riders


# api to get all rides
@api_view(["GET"])
def get_all_rides(request):
    rides = Ride.objects.all().order_by("-requested_at")
    serializer = RideSerializer(rides, many=True)
    return Response(serializer.data)

# end of api to get all rides


# payments/views.py
@api_view(["GET"])
def get_all_payments(request):
    payments = Payment.objects.select_related("ride__rider", "ride__driver__user").all().order_by("-paid_at")
    serializer = PaymentSerializer(payments, many=True)
    return Response(serializer.data)
# end of payments/views.py


# api to get dashboard stats
@api_view(['GET'])
def dashboard_stats(request):
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    # Total counts
    total_riders = User.objects.filter(role="rider").count()
    total_drivers = User.objects.filter(role="driver").count()
    total_rides = Ride.objects.count()

    # Earnings - only successful payments
    daily_earnings = Payment.objects.filter(
        status="success", paid_at__date=today
    ).aggregate(total=Sum("amount"))["total"] or 0

    weekly_earnings = Payment.objects.filter(
        status="success", paid_at__date__gte=start_of_week
    ).aggregate(total=Sum("amount"))["total"] or 0

    monthly_earnings = Payment.objects.filter(
        status="success", paid_at__date__gte=start_of_month
    ).aggregate(total=Sum("amount"))["total"] or 0

    yearly_earnings = Payment.objects.filter(
        status="success", paid_at__date__gte=start_of_year
    ).aggregate(total=Sum("amount"))["total"] or 0

    data = {
        "total_riders": total_riders,
        "total_drivers": total_drivers,
        "total_rides": total_rides,
        "daily_earnings": daily_earnings,
        "weekly_earnings": weekly_earnings,
        "monthly_earnings": monthly_earnings,
        "yearly_earnings": yearly_earnings,
    }

    serializer = DashboardStatsSerializer(data)
    return Response(serializer.data)
# end of api to get dashboard stats

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


# paystack initialize payment
PAYSTACK_SECRET_KEY = "sk_test_a60107fb70a0a8424b1ce810d3c677a4229b168e"
@api_view(["POST"])
def initialize_payment(request):
    amount = request.data.get("amount")   # ✅ you are sending this
    email = request.data.get("email", "customer@email.com")  # fallback email
    transaction_reference = request.data.get("transaction_reference")
    metadata = request.data.get("metadata", {})
    rider_id = request.data.get("rider_id")
    driver_id = request.data.get("driver_id")
    pickup_lat = request.data.get("pickup_lat")
    pickup_lng = request.data.get("pickup_lng")
    dropoff_lat = request.data.get("dropoff_lat")
    dropoff_lng = request.data.get("dropoff_lng")
    distance_km = request.data.get("distance_km")
    estimated_fare = request.data.get("estimated_fare")
    phone_number = request.data.get("phone_number", "N/A")
    print("Rider Id:", rider_id, "Driver Id:", driver_id, "Amount:", amount, "Reference:", transaction_reference)

    if not amount:
        return Response({"error": "Amount is required"}, status=400)

    try:
        amount = int(float(amount) * 100)  # convert to Kobo
    except Exception:
        return Response({"error": "Invalid amount"}, status=400)

    # ✅ 2. Check if rider has an incomplete ride
    existing_ride = Ride.objects.filter(
        rider=rider_id, 
        status__in=["pending","accepted", "ongoing"]
    ).first()

    if existing_ride:
        return JsonResponse({
            "error": "You already have an active ride.",
            "ride_id": existing_ride.id,
            "status": existing_ride.status
        }, status=210)

    payload = {
        "email": email,
        "amount": amount,
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
        }
    }
    # print("INITIALIZE PAYLOAD:", payload)

    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    res = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)

    return Response(res.json())




# paystack payment callback

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
                status="success",
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
                message=f"Your ride {ride.id} has been successfully booked and paid (KES {total_amount})."
            )
            if driver:
                Notification.objects.create(
                    user=driver.user,
                    message=f"You have been assigned ride {ride.id}. Pickup at ({ride.pickup_lat}, {ride.pickup_lng})."
                )
                send_push_notification(
                    driver.user.expo_token,
                    "Ride Assigned",
                    f"You have been assigned ride {ride.id}. Be sure to pick up the rider on time.",
                    {"ride_id": ride.id}
                )

        return render(request, "payment_status.html", {
            "status": "success",
            "ride": ride,
            "payment": payment,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)



# api to update driver status and verification
@api_view(["PATCH"])
def update_driver_status(request, driver_id):
    try:
        driver = Driver.objects.get(id=driver_id)
        new_status = request.data.get("status")
        new_verified = request.data.get("verified")

        has_changed = False

        if new_status and new_status != driver.status:
            driver.status = new_status
            has_changed = True

        if new_verified is not None and new_verified != driver.verified:
            driver.verified = new_verified
            has_changed = True

        driver.save()

        if has_changed:
            send_push_notification(
                driver.user.expo_token,
                "Update",
                f"Your status has changed: Status: {driver.status}, Verified: {driver.verified}",
                {}
            )

        return Response({"message": "Driver updated successfully"}, status=200)
    except Driver.DoesNotExist:
        return Response({"error": "Driver not found"}, status=404)


