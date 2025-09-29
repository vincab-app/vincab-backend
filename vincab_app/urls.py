from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signin/', views.signin, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('driversignup/', views.driversignup, name='driversignup'),
    path('reset_password/<str:email>/', views.reset_password, name='reset_password'),
    path('get_user_notifications/<str:user_id>/', views.get_user_notifications, name='get_user_notifications'),
    path('nearby_vehicles/<str:lat>/<str:lng>/', views.nearby_vehicles, name='nearby_vehicles'),
    path('create_ride_and_payment/', views.create_ride_and_payment, name='create_ride_and_payment'),
    path('create_rating/', views.create_rating, name='create_rating'),
    path('get_user_ratings/<int:user_id>/', views.get_user_ratings, name='get_user_ratings'),
    path('get_all_payments/', views.get_all_payments, name='get_all_payments'),
    path('get_driver_payments/<int:driver_id>/', views.get_driver_payments, name='get_driver_payments'),
    path('get_requested_rides/<int:user_id>/', views.get_requested_rides, name='get_requested_rides'),
    path('update_ride_status/', views.update_ride_status, name='update_ride_status'),
    path('send_expo_token/<int:user_id>/<str:expo_token>/', views.send_expo_token, name='send_expo_token'),
    path('notify_driver/', views.notify_driver, name='notify_driver'),
    path('get_driver_total_earnings/<int:user_id>/', views.get_driver_total_earnings, name='get_driver_total_earnings'),
    path('get_vincab_earnings/', views.get_vincab_earnings, name='get_vincab_earnings'),
    path('calculate_fare/<str:pickup_lat>/<str:pickup_lng>/<str:drop_lat>/<str:drop_lng>/', views.calculate_fare, name='calculate_fare'),
    path('get_ride_details/<int:rider_id>/', views.get_ride_details, name='get_ride_details'),
    path('check_driver_verified/<int:user_id>/', views.check_driver_verified, name='check_driver_verified'),
    path('update_rider_profile/', views.update_rider_profile, name='update_rider_profile'),
]
