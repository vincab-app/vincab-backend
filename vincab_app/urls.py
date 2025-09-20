from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signin/', views.signin, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('reset_password/<str:email>/', views.reset_password, name='reset_password'),
    path('get_user_notifications/<str:user_id>/', views.get_user_notifications, name='get_user_notifications'),
    path('nearby_vehicles/<str:lat>/<str:lng>/', views.nearby_vehicles, name='nearby_vehicles'),
]
