from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signin/', views.signin, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('reset_password/<str:email>/', views.reset_password, name='reset_password'),
    path('get_user_notifications/<str:user_id>/', views.get_user_notifications, name='get_user_notifications'),
    path('nearby_vehicles/<str:lat>/<str:lng>/', views.nearby_vehicles, name='nearby_vehicles'),
    path('create_ride_and_payment/', views.create_ride_and_payment, name='create_ride_and_payment'),
    path('create_rating/', views.create_rating, name='create_rating'),
    path('get_user_ratings/<int:user_id>/', views.get_user_ratings, name='get_user_ratings'),
    path('get_all_payments/', views.get_all_payments, name='get_all_payments'),
    path('get_driver_payments/<int:driver_id>/', views.get_driver_payments, name='get_driver_payments'),
    path('get_requested_rides/<int:user_id>/', views.get_requested_rides, name='get_requested_rides'),
]
