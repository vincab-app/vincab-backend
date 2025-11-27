import requests
from requests.auth import HTTPBasicAuth

CONSUMER_KEY = 'Jl8NQACFGn5Sz3IOjeetjpTNU7FqtAWs5tdd3WdPy3J6KMYh'
CONSUMER_SECRET = 'DAbG0G5EAVB0lNOPaLGEsCXN8azmSgKgGnIw9q1Zi6hmXvKojBE9r0CJR4MByqvw'
OAUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

def get_access_token():
    response = requests.get(OAUTH_URL, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET))
    if response.status_code == 200:
        access_token = response.json()['access_token']
        return access_token
    else:
        return None
