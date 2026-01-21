# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.timezone import now
from django.db.models import Sum, Q
from django.db import transaction
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string

# REST framework imports
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

# Third-party imports
import pyrebase
import firebase_admin
from firebase_admin import auth, credentials
import cloudinary.uploader
import requests
import json
from geopy.distance import geodesic
from decimal import Decimal
from datetime import timedelta

# Local imports
from vincab_app.models import User, Notification, Vehicle, Ride, Payment, Driver, Rating, DriverPayment
from vincab_app.serializers import (
    NotificationSerializer,
    VehicleSerializer,
    DriverSerializer,
    RideSerializer,
    PaymentSerializer,
    DashboardStatsSerializer
)
from vincab_app.utils import get_access_token, normalize_phone

# Logging
import logging
logger = logging.getLogger("backend")

# System
import os
