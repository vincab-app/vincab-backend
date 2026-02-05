from .common_imports import *
from .helper import *
from .auth import verify_firebase_token

# admin api to get all drivers
@api_view(['GET'])
@verify_firebase_token
def get_all_drivers(request):
    drivers = Driver.objects.select_related("user").prefetch_related("vehicles").all()
    serializer = DriverSerializer(drivers, many=True)
    return Response(serializer.data)
# end of admin api to get all drivers


# api to get all riders
@api_view(['GET'])
@verify_firebase_token
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
                "profile_image": rider.profile_image.url if rider.profile_image else None,
                "current_lat": rider.current_lat,
                "current_lng": rider.current_lng,
                "date_joined": rider.date_joined,
                "expo_token": rider.expo_token,
            })

        return JsonResponse({"riders": riders_data}, status=200, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
# end of api to get all riders

# api to get a single rider
@api_view(['GET'])
@verify_firebase_token
def get_single_rider(request, rider_id):
    try:
        rider = User.objects.get(id=rider_id, role="rider")

        rider_data = {
            "id": rider.id,
            "full_name": rider.full_name,
            "email": rider.email,
            "phone_number": rider.phone_number,
            "profile_image": rider.profile_image.url if rider.profile_image else None,
            "current_lat": rider.current_lat,
            "current_lng": rider.current_lng,
            "date_joined": rider.date_joined,
            "expo_token": rider.expo_token,
            "phone_verified": rider.phone_verified,
            "is_active": rider.is_active,   # useful for block/recover
        }

        return JsonResponse({"rider": rider_data}, status=200)

    except User.DoesNotExist:
        return JsonResponse({"error": "Rider not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
# end of api to get single rider


# api for admin actions
@api_view(['POST'])
@verify_firebase_token
def admin_rider_action(request):
    uid = request.data.get("user_id")
    action = request.data.get("action")

    rider = get_object_or_404(User, id=uid, role="rider")

    try:
        # BLOCK USER
        if action == "block":
            rider.is_active = False
            rider.save()
            return Response({"message": "Rider blocked successfully"})

        # RECOVER USER
        elif action == "recover":
            rider.is_active = True
            rider.phone_verified = False
            rider.save()
            return Response({"message": "Rider recovered successfully"})

        # DELETE USER (LOCAL + FIREBASE)
        elif action == "delete":
            firebase_uid = rider.firebase_uid  #must exist in DB

            # DELETE FROM FIREBASE AUTH
            try:
                auth.delete_user(firebase_uid)
            except auth.UserNotFoundError:
                pass  # Already deleted or never existed

            # DELETE FROM DJANGO DB
            rider.delete()

            return Response({"message": "Rider deleted completely"})

        else:
            return Response({"error": "Invalid action"}, status=400)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


# end of api for admin actions


# api to get all rides
@api_view(["GET"])
@verify_firebase_token
def get_all_rides(request):
    rides = Ride.objects.all().order_by("-requested_at")
    serializer = RideSerializer(rides, many=True)
    return Response(serializer.data)

# end of api to get all rides


# payments/views.py
@api_view(["GET"])
@verify_firebase_token
def get_all_payments(request):
    payments = Payment.objects.select_related("ride__rider", "ride__driver__user").all().order_by("-paid_at")
    serializer = PaymentSerializer(payments, many=True)
    return Response(serializer.data)
# end of payments/views.py


# api to get dashboard stats
@api_view(['GET'])
@verify_firebase_token
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
        status="paid", paid_at__date=today
    ).aggregate(total=Sum("amount"))["total"] or 0

    weekly_earnings = Payment.objects.filter(
        status="paid", paid_at__date__gte=start_of_week
    ).aggregate(total=Sum("amount"))["total"] or 0

    monthly_earnings = Payment.objects.filter(
        status="paid", paid_at__date__gte=start_of_month
    ).aggregate(total=Sum("amount"))["total"] or 0

    yearly_earnings = Payment.objects.filter(
        status="paid", paid_at__date__gte=start_of_year
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

# api to update driver status and verification
@api_view(["PATCH"])
@verify_firebase_token
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

# api for admin to send push notifications to all users
@api_view(["POST"])
@verify_firebase_token
def send_push_notification_to_all_users(request):
    try:
        message = request.data.get("message")
        title = request.data.get("title")
        data = request.data.get("data")

        users = User.objects.all()
        for user in users:
            send_push_notification(user.expo_token, title, message, data)

        return Response({"message": "Push notifications sent successfully"}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

# api to get vincab earnings
@api_view(["GET"])
@verify_firebase_token
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
