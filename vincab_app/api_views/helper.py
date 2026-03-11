from .common_imports import *

# send push notification to phne
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

def send_push_notification(token, title, body, data=None):
    if not token:
        return {"error": "No push token provided."}

    message = {
        "to": f"{token}",
        "sound": "default",
        "title": f"{title}",
        "body": f"{body}",
        "data": data or {},
    }

    try:
        response = requests.post(EXPO_PUSH_URL, json=message)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


# 🔹 Helper: Reverse Geocoding using OpenStreetMap (Free)
def reverse_geocode(lat, lng):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        headers = {"User-Agent": "VinCab/1.0 (contact@vincab.com)"}
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        address = data.get("address", {})
        return f"{address.get('city', '')}, {address.get('country', '')}"
    except Exception as e:
        print("Reverse geocode error:", e)
        return None


# calculate the time btwn vehicle and rider's pick location
def get_eta(vehicle_lat, vehicle_lng, pickup_lat, pickup_lng):
    url = f"https://router.project-osrm.org/route/v1/driving/{vehicle_lng},{vehicle_lat};{pickup_lng},{pickup_lat}?overview=false"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        if data.get("routes"):
            duration_seconds = data["routes"][0]["duration"]
            distance_meters = data["routes"][0]["distance"]
            return {
                "eta_minutes": round(duration_seconds / 60, 1),
                "distance_km": round(distance_meters / 1000, 2),
            }
    return None

# generate random codes for pick and complete

def generate_code():
    return str(secrets.randbelow(900000) + 100000)

# function to calculate fare
def calculate_fare(driver_location, pickup_lat, pickup_lng, drop_lat, drop_lng):

    driver = (driver_location[0], driver_location[1])
    pickup = (float(pickup_lat), float(pickup_lng))
    drop = (float(drop_lat), float(drop_lng))

    # Distances
    driver_to_rider = geodesic(driver, pickup).km
    rider_to_destination = geodesic(pickup, drop).km

    # Total distance for fare
    trip_distance = rider_to_destination + driver_to_rider

    # Pricing parameters
    base_fare = 50            # KES
    price_per_km = 40          # KES/km
    price_per_minute = 4       # KES/min
    avg_speed_kmh = 40         # average city speed
    minimum_fare = 200         # minimum ride price
    surge_multiplier = 1.0     # change during high demand

    # Estimate trip time
    trip_time_minutes = (trip_distance / avg_speed_kmh) * 60

    # Fare calculation
    fare = (
        base_fare +
        (trip_distance * price_per_km) +
        (trip_time_minutes * price_per_minute)
    )

    # Apply surge
    fare = fare * surge_multiplier

    # Ensure minimum fare
    fare = max(fare, minimum_fare)

    return round(trip_distance, 2), round(fare, 2)
