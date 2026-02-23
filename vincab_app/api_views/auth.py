from .common_imports import *


config = {
    "apiKey": os.environ.get("FIREBASE_API_KEY"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN"),
    "databaseURL": os.environ.get("FIREBASE_DATABASE_URL"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.environ.get("FIREBASE_APP_ID"),
    "measurementId": os.environ.get("FIREBASE_MEASUREMENT_ID")
}
firebase = pyrebase.initialize_app(config)
authe = firebase.auth() 
database = firebase.database()

# Initialize Firebase once (e.g., in settings.py or a startup file)
service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
# cred = credentials.Certificate("serviceAccountKey.json")
cred = credentials.Certificate(service_account_info)
# firebase_admin.initialize_app(cred)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

def verify_firebase_token(view_func):
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JsonResponse({"error": "Authorization header missing"}, status=401)

        try:
            token = auth_header.split(" ")[1]  # "Bearer <token>"
            decoded = auth.verify_id_token(token)
            request.firebase_uid = decoded["uid"]   # <===== IMPORTANT
        except Exception as e:
            return JsonResponse({"error": "Invalid token", "details": str(e)}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper

# api to refresh token
@api_view(["POST"])
def refresh_token(request):
    refresh_token = request.data.get("refresh_token")

    if not refresh_token:
        return JsonResponse({"message": "Refresh token is required"}, status=400)

    try:
        # Pyrebase refresh
        new_tokens = authe.refresh(refresh_token)

        return JsonResponse({
            "access_token": new_tokens["idToken"],
            "refresh_token": new_tokens["refreshToken"],
            "expires_in": new_tokens["expiresIn"],
        })

    except Exception as e:
        return JsonResponse({
            "message": "Failed to refresh token",
            "error": str(e)
        }, status=401)

# api to get user data when sigin in with googel from frontend
@api_view(['POST'])
def google_signin(request):
    id_token = request.data.get("id_token")
    print(id_token)
    try:
        # Verify the token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token['email']
        name = decoded_token.get('name', '')

        # Check if user exists in Django db
        db_user = User.objects.filter(firebase_uid=uid).first()

        if not db_user:
            # Create new user
            db_user = User.objects.create(
                firebase_uid=uid,
                full_name=name,
                email=email,
                role='rider'
            )
            # send notification
            Notification.objects.create(
                user=db_user,
                message="Welcome to VinCab! Your account has been created successfully.",
                is_read=False
            )

        # Return user data
        return JsonResponse({
            "message": "Sign-in successful",
            "access_token": id_token,
            "refresh_token": "",  # Google sign-in does not provide a refresh token here
            "expires_in": 3600,  # Token validity duration
            "user": {
                "user_id": db_user.id,
                "user_name": db_user.full_name,
                "user_email": db_user.email,
                "phone_number": db_user.phone_number,
                "role": db_user.role,
                "phone_verified": db_user.phone_verified,
                "profile_image": db_user.profile_image.url if db_user.profile_image else None,
                "date_joined": db_user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
            }
        })

    except Exception as e:
        print("Google sign-in error:", str(e))
        return JsonResponse({"message": "Invalid token", "error": str(e)}, status=401)

# check authentication status api
@api_view(['GET'])
@verify_firebase_token
def auth_check(request):
    return JsonResponse({
        "authenticated": True,
        "uid": request.firebase_uid
    })
        

# start of siginin
@api_view(['POST'])
def signin(request):
    email = request.data.get("email")
    password = request.data.get("password")

    try:
        # Try Firebase sign in
        login = authe.sign_in_with_email_and_password(email, password)
        id_token = login["idToken"]
        refresh_token = login["refreshToken"]
        expires_in = login["expiresIn"]

        # Get account info
        info = authe.get_account_info(id_token)
        email_verified = info["users"][0]["emailVerified"]

        if not email_verified:
            # Resend verification email
            authe.send_email_verification(id_token)

            return JsonResponse({
                "message": "Email not verified. Verification link has been sent again."
            }, status=403)

        # Email verified → Continue login
        uid = info["users"][0]["localId"]
        db_user = User.objects.filter(firebase_uid=uid).first()
        # log user action
        logger.info(f"User sign in: Email: {email}, Name: {db_user.full_name}")

        return JsonResponse({
            "message": "Login successful",
            "access_token": id_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "user": {
                "user_id": db_user.id,
                "user_name": db_user.full_name,
                "user_email": db_user.email,
                "phone_number": db_user.phone_number,
                "role": db_user.role,
                "phone_verified": db_user.phone_verified,
                "profile_image": db_user.profile_image.url if db_user.profile_image else None,
                "date_joined": db_user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
            }
        })

    except Exception as e:
        return JsonResponse({"message": "Invalid login", "error": str(e)}, status=401)
# end

# start of signup
@csrf_exempt
@api_view(['POST'])
def signup(request):
    data = request.data
    full_name = data.get("full_name")
    phone_number = data.get("phone_number")
    email = data.get("email")
    password = data.get("password")

    if not all([full_name, phone_number, email, password]):
        return JsonResponse({"message": "Missing fields"}, status=400)

    # check if email already exists in firebase
    try:
        existing_user = authe.get_user_by_email(email)
        return JsonResponse({"message": "Email already exists"}, status=400)
    except:
        pass  # user does not exist, continue

    try:
        # Create user in Firebase
        user = authe.create_user_with_email_and_password(email, password)

        # Send verification email
        authe.send_email_verification(user['idToken'])

        # Save profile to Django database (NO PASSWORD)
        uid = user["localId"]
        User.objects.create(
            firebase_uid=uid,
            full_name=full_name,
            phone_number=phone_number,
            email=email
        )
        # log user action
        logger.info(f"User sign up: Email: {email}, Name: {full_name}")

        # create welcome notification
        db_user = User.objects.get(firebase_uid=uid)
        Notification.objects.create(
            user=db_user,
            message="Welcome to VinCab! Your account has been created successfully.",
            is_read=False
        )

        return JsonResponse({"message": "Account created. Check your email to verify."}, status=201)

    except Exception as e:
        return JsonResponse({"message": "Signup failed", "error": str(e)}, status=400)
# end

# api to mark phone as verified
@api_view(['POST'])
@verify_firebase_token
def verify_phone(request):
    firebase_uid = request.firebase_uid

    try:
        user = User.objects.get(firebase_uid=firebase_uid)
        user.phone_verified = True
        user.save()

        # send notification
        Notification.objects.create(
            user=user,
            message="Phone number verified successfully.",
            is_read=False
        )

        return JsonResponse({"message": "Phone number verified successfully"}, status=200)

    except User.DoesNotExist:
        return JsonResponse({"message": "User not found"}, status=404)
# end of phone verification api

# start of delete account api
@api_view(['DELETE'])
@verify_firebase_token
def delete_account(request):
    firebase_uid = request.firebase_uid

    # 1. Delete from Firebase Auth
    try:
        auth.delete_user(firebase_uid)
        print("Firebase user deleted")
    except Exception as e:
        print("Firebase delete error:", e)

    # 2. Delete from Django database
    user = User.objects.filter(firebase_uid=firebase_uid).first()
    if user:
        user.delete()

    return JsonResponse({"message": "Account deleted successfully"}, status=200)
# end

# request password reset api
@api_view(['POST'])
def request_password_reset(request):
    email = request.data.get("email")

    try:
        authe.send_password_reset_email(email)
        return JsonResponse({"message": "Password reset email sent"})
    except Exception as e:
        return JsonResponse({"message": "Error sending reset email", "error": str(e)}, status=400)
# end

# start of driver signup api
@csrf_exempt
@api_view(['POST'])
def driversignup(request):
    if request.method != 'POST':
        return JsonResponse({"message": "Invalid request method"}, status=405)

    try:
        data = request.data
        full_name = data.get("full_name")
        phone_number = data.get("phone_number")
        email = data.get("email")
        license_number = data.get("license_number")
        password = data.get("password")
        car_make = data.get("vehicle_make")
        car_model = data.get("vehicle_model")
        car_plate = data.get("vehicle_plate")
        car_color = data.get("vehicle_color")
        vehicle_type = data.get("vehicle_type")
        expo_token = data.get("expo_token")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        car_image = request.FILES.get("vehicle_image")
        id_number = request.FILES.get("id_number")
        profile_image = request.FILES.get("profile_image")
        id_front_image = request.FILES.get("id_front_image")
        id_back_image = request.FILES.get("id_back_image")

        if not all([full_name, email, password, phone_number, id_number, license_number, car_make, car_model, car_plate, car_color, vehicle_type, expo_token]):
            return JsonResponse({"message": "Missing required fields"}, status=400)

        # Check if email already exists in Firebase
        try:
            existing_user = authe.get_user_by_email(email)
            return JsonResponse({"message": "Email already exists"}, status=400)
        except:
            pass  # user does not exist, continue

        # Create user in Firebase Auth
        firebase_user = authe.create_user_with_email_and_password(email, password)

        # Send Firebase email verification
        authe.send_email_verification(firebase_user['idToken'])

        # Save user to Django DB
        user = User.objects.create(
            full_name=full_name,
            phone_number=phone_number,
            email=email,
            role="driver",
            profile_image=profile_image,
            firebase_uid=firebase_user['localId'],
            current_lat=latitude or 0.0,
            current_lng=longitude or 0.0,
            expo_token=expo_token,
        )

        # Save driver info
        driver = Driver.objects.create(
            user=user,
            license_number=license_number,
            id_number=id_number,
            id_front_image=id_front_image,
            id_back_image=id_back_image,
            verified=False,
            rating=0,
            status="inactive"
        )

        Vehicle.objects.create(
            driver=driver,
            plate_number=car_plate,
            model=car_model,
            vehicle_type=vehicle_type,
            color=car_color,
            car_image=car_image
        )
        # create a driverpayment record for the driver
        DriverPayment.objects.create(
            driver=driver,
            amount=0.0,
            pending_amount=0.0
        )

        # Notifications
        Notification.objects.create(
            user=user,
            message="Welcome to VinCab! Your account has been created successfully.",
            is_read=False
        )
        Notification.objects.create(
            user=user,
            message="Your request to be a driver at VinCab was received successfully. We'll get back to you within 48 hours.",
            is_read=False
        )

        return JsonResponse({"message": "Successfully signed up. Please check your email to verify your account."}, status=201)

    except Exception as e:
        print("Error:", str(e))
        return JsonResponse({"message": "Signup failed", "error": str(e)}, status=400)

#end of driver signup api
