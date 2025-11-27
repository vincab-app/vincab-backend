from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# -----------------------------
# 1. User Model
# -----------------------------
class User(models.Model):
    ROLE_CHOICES = [
        ('rider', 'Rider'),
        ('driver', 'Driver'),
        ('admin', 'Admin'),
    ]
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, unique=True)
    email = models.CharField(max_length=100, default="johndoe@example.com")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="rider")
    firebase_uid = models.CharField(max_length=256, default="@vincab2025")
    current_lat = models.FloatField(null=True, blank=True, default=0.0)
    current_lng = models.FloatField(null=True, blank=True, default=0.0)
    phone_verified = models.BooleanField(default=False)
    profile_image = models.URLField(blank=True, null=True, default='https://res.cloudinary.com/dc68huvjj/image/upload/v1748119193/zzy3zwrius3kjrzp4ifc.png')
    date_joined = models.DateTimeField(default=timezone.now)
    expo_token = models.CharField(max_length=100, default="hsvsx92jjs")

    def __str__(self):
        return f"{self.full_name} ({self.role})"




# -----------------------------
# 2. Driver Model
# -----------------------------
class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="driver_profile")
    license_number = models.CharField(max_length=50, unique=True)
    verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5.0)
    status = models.CharField(max_length=20, default="inactive")  # active, busy, inactive

    def __str__(self):
        return f"Driver: {self.user.full_name}"


# -----------------------------
# 3. Vehicle Model
# -----------------------------
class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('car', 'Car'),
        ('bike', 'Bike'),
        ('van', 'Van'),
    ]
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField(max_length=20, unique=True)
    model = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    color = models.CharField(max_length=30)
    capacity = models.IntegerField(default=4)
    car_image = models.URLField(blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.model} ({self.plate_number})"


# -----------------------------
# 4. Ride Model
# -----------------------------
class Ride(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rides_as_rider")
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name="rides_as_driver")
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()
    dropoff_lat = models.FloatField()
    dropoff_lng = models.FloatField()
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ride {self.id} - {self.rider.full_name} ({self.status})"


# -----------------------------
# 5. Payment Model
# -----------------------------
class Payment(models.Model):
    METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Card'),
        ('wallet', 'Wallet'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.method}"


# -----------------------------
# 6. Rating Model
# -----------------------------
class Rating(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="ratings")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_ratings")
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_ratings")
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.rating} for {self.reviewee.full_name}"


# -----------------------------
# 7. Notification Model
# -----------------------------
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.full_name}"

class DriverPayment(models.Model):
    driver = models.ForeignKey("Driver", on_delete=models.CASCADE, related_name="driver_payments")
    payment = models.OneToOneField("Payment", on_delete=models.CASCADE, related_name="driver_payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # driver’s 80%
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DriverPayment {self.id} - {self.driver.user.full_name} {self.amount}"

