from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import pyrebase
from .models import User, Notification, Vehicle
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import NotificationSerializer, VehicleSerializer
from geopy.distance import geodesic
from rest_framework.response import Response


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
                return JsonResponse({"message": "Successfully logged in", "token":session_id, "user_id":user_id, "user_name":user_name,"user_email":email,"phone_number":phone_number,"role":role, "profile_image":profile_image, "date_joined":date_joined}, status=200)
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


@api_view(["GET"])
def nearby_vehicles(request, lat, lng):
    try:
        # customer_lat = float(request.query_params.get("lat"))
        # customer_lng = float(request.query_params.get("lng"))
        customer_lat = float(lat)
        customer_lng = float(lng)
    except (TypeError, ValueError):
        return Response({"error": "lat and lng query params are required"}, status=400)

    customer_location = (customer_lat, customer_lng)

    vehicles = Vehicle.objects.all()
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
        vehicle_data.append(data)

    # Sort by ETA
    sorted_vehicles = sorted(vehicle_data, key=lambda x: x["eta_minutes"])

    return Response(sorted_vehicles)
