from rest_framework import serializers
from .models import Notification, Vehicle, User, Driver, Ride, Payment

class NotificationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'is_read']

class VehicleSerializer(serializers.ModelSerializer):
    eta_minutes = serializers.FloatField(read_only=True)

    class Meta:
        model = Vehicle
        fields = "__all__"


# sadmin serializers
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "full_name", "phone_number", "email", "role",
            "current_lat", "current_lng", "profile_image", "date_joined",
        ]

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "id", "plate_number", "model", "vehicle_type", 
            "color", "capacity", "car_image", "date_joined"
        ]

class DriverSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    vehicles = VehicleSerializer(many=True)

    class Meta:
        model = Driver
        fields = [
            "id", "user", "license_number", "verified",
            "rating", "status", "vehicles"
        ]


# rides/serializers.py
class RideSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(source="rider.full_name", read_only=True)
    driver_name = serializers.CharField(source="driver.user.full_name", read_only=True)

    class Meta:
        model = Ride
        fields = [
            "id",
            "rider_name",
            "driver_name",
            "pickup_lat",
            "pickup_lng",
            "dropoff_lat",
            "dropoff_lng",
            "distance_km",
            "estimated_fare",
            "status",
            "requested_at",
            "completed_at",
        ]


# payments/serializers.py
class PaymentSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(source="ride.rider.full_name", read_only=True)
    driver_name = serializers.CharField(source="ride.driver.user.full_name", read_only=True)
    driver_id = serializers.IntegerField(source="ride.driver.id", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "ride",
            "rider_name",
            "driver_name",
            "driver_id",
            "amount",
            "method",
            "status",
            "transaction_reference",
            "paid_at",
        ]


class DashboardStatsSerializer(serializers.Serializer):
    total_riders = serializers.IntegerField()
    total_drivers = serializers.IntegerField()
    total_rides = serializers.IntegerField()
    daily_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    weekly_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    yearly_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)

