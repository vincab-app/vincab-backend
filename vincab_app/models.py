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
    last_updated_location = models.DateTimeField(default=timezone.now)
    current_lng = models.FloatField(null=True, blank=True, default=0.0)
    phone_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    profile_image = models.URLField(default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png")
    date_joined = models.DateTimeField(default=timezone.now)
    expo_token = models.CharField(max_length=100, default="hsvsx92jjs")

    def __str__(self):
        return f"#{self.id} {self.full_name} ({self.role})"




# -----------------------------
# 2. Driver Model
# -----------------------------
class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="driver_profile")
    license_number = models.CharField(max_length=50, unique=True)
    id_number = models.CharField(max_length=8, default="12345678")
    id_front_image = models.URLField(default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png")
    id_back_image = models.URLField(default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png")
    verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5.0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, default="inactive")  # active, busy, inactive

    def __str__(self):
        return f"#{self.id} Driver: {self.user.full_name}"


# -----------------------------
# 3. Vehicle Model
# -----------------------------
class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('car', 'Car'),
        ('bike', 'Bike'),
        ('van', 'Van'),
        ('motorbike', 'Motorbike'),
    ]
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField(max_length=20, unique=True)
    model = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    color = models.CharField(max_length=30)
    capacity = models.IntegerField(default=4)
    car_image = models.URLField(default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png")
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
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('picked', 'Picked'),
    ]

    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rides_as_rider")
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name="rides_as_driver")
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()
    pickup_address = models.CharField(max_length=100, default="")
    dropoff_lat = models.FloatField()
    dropoff_lng = models.FloatField()
    dropoff_address = models.CharField(max_length=100, default="")
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    driver_arrived_notified = models.BooleanField(default=False)
    pick_code = models.IntegerField(null=True, blank=True)
    complete_code = models.IntegerField(null=True, blank=True)
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
        ('paystack', 'Paystack')
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name="payment")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    checkout_request_id = models.CharField(max_length=100, default="")
    merchant_request_id = models.CharField(max_length=100, default="")
    receipt_number = models.CharField(max_length=50, blank=True, null=True, default="")
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
    reviewee = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="received_ratings")
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.rating} for {self.reviewee.user.full_name}"


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
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0) 
    float_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    pending_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.id} DriverPayment {self.driver.user.full_name} {self.amount}"

class Withdraw(models.Model):
    driver = models.ForeignKey("Driver", on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=10, decimal_places=2) 
    transactionRef = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.id} Withdraw {self.driver.user.full_name} {self.amount} ({self.transactionRef})"

