from rest_framework import serializers
from .models import Notification, Vehicle

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