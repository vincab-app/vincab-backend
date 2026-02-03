from django.urls import path
from . import views
from vincab_app.api_views.auth import *
from vincab_app.api_views.driver import *
from vincab_app.api_views.rider import *
from vincab_app.api_views.admin import *
from vincab_app.api_views.payments import *

urlpatterns = [
    path('', views.index, name='index'),
    path('refresh_token', refresh_token, name='refresh_token'),
    path('auth_check/', auth_check, name='auth_check'),
    path('google_signin/', google_signin, name='google_signin'),
    path('signin/', signin, name='signin'),
    path('delete_account/', delete_account, name='delete_account'),
    path('verify_phone/', verify_phone, name='verify_phone'),
    path('signup/', signup, name='signup'),
    path('request_password_reset/', request_password_reset, name='request_password_reset'),
    path('driversignup/', driversignup, name='driversignup'),

    path('get_user_notifications/<str:user_id>/', get_user_notifications, name='get_user_notifications'),
    path('nearby_vehicles/<str:lat>/<str:lng>/', nearby_vehicles, name='nearby_vehicles'),
    path('create_ride_and_payment/', create_ride_and_payment, name='create_ride_and_payment'),
    path('create_rating/', create_rating, name='create_rating'),
    path('get_user_ratings/<int:user_id>/', get_user_ratings, name='get_user_ratings'),
    path('get_all_payments/', get_all_payments, name='get_all_payments'),
    path('get_driver_payments/<int:driver_id>/', get_driver_payments, name='get_driver_payments'),
    path('get_requested_rides/<int:user_id>/', get_requested_rides, name='get_requested_rides'),
    path('payout_view/', payout_view, name='payout_view'),
    path('update_ride_status/', update_ride_status, name='update_ride_status'),
    path('send_expo_token/<int:user_id>/<str:expo_token>/', send_expo_token, name='send_expo_token'),
    path('notify_driver/', notify_driver, name='notify_driver'),
    path('get_driver_total_earnings/<int:user_id>/', get_driver_total_earnings, name='get_driver_total_earnings'),
    path('get_vincab_earnings/', get_vincab_earnings, name='get_vincab_earnings'),
    path('calculate_fare/<str:pickup_lat>/<str:pickup_lng>/<str:drop_lat>/<str:drop_lng>/', calculate_fare, name='calculate_fare'),
    path('get_ride_details/<int:rider_id>/', get_ride_details, name='get_ride_details'),

    # path('lipa_na_mpesa/<str:phone_number>/<str:amount>/', views.lipa_na_mpesa, name='lipa_na_mpesa'),
    path('mpesa_callback/', mpesa_callback, name='mpesa_callback'),
    # path('send_b2c_payment/<str:phone_number>/<str:amount>/', views.send_b2c_payment, name='send_b2c_payment'),
    path('b2c_callback/', b2c_callback, name='b2c_callback'),


    path('get_completed_rides/<int:rider_id>/', get_completed_rides, name='get_completed_rides'),
    path('check_driver_verified/<int:user_id>/', check_driver_verified, name='check_driver_verified'),
    path('update_rider_profile/', update_rider_profile, name='update_rider_profile'),
    path('get_all_drivers/', get_all_drivers, name='get_all_drivers'),
    path('get_all_riders/', get_all_riders, name='get_all_riders'),
    path('get_single_rider/<int:rider_id>/', get_single_rider, name='get_single_rider'),
    path('admin_rider_action/', admin_rider_action, name='admin_rider_action'),
    path('get_all_rides/', get_all_rides, name='get_all_rides'),
    path('dashboard_stats/', dashboard_stats, name='dashboard_stats'),
    path('update_location/', update_location, name='update_location'),
    path('initialize_payment/', initialize_payment, name='initialize_payment'),
    path('confirm_ride/', confirm_ride, name='confirm_ride'),
    path('payment_callback/', payment_callback, name='payment_callback'),
    path('update_driver_status/<int:driver_id>/', update_driver_status, name='update_driver_status'),
    path('send_push_notification/', send_push_notification_to_all_users, name='send_push_notification_to_all_users'),
    path("driver_location/<int:driver_id>/", get_driver_location, name="driver_location"),
    
]
