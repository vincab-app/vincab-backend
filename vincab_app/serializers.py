from rest_framework import serializers
from .models import Notification, Vehicle, User, Driver

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
