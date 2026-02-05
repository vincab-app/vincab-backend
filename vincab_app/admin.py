from django.contrib import admin
from .models import User, Driver, Vehicle, Ride, Payment, Rating, Notification, DriverPayment, Withdraw

# Register your models here.
admin.site.register(User)
admin.site.register(Driver)
admin.site.register(Vehicle)
admin.site.register(Ride)
admin.site.register(Payment)
admin.site.register(Rating)
admin.site.register(Notification)
admin.site.register(DriverPayment)
admin.site.register(Withdraw)