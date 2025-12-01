import requests
from requests.auth import HTTPBasicAuth

DARAJA_CONSUMER_KEY = '0gLMpK04PuF3KweF5Nx3KH5t5SS46ldqz0w8WzKAnyNJfA1L'
DARAJA_CONSUMER_SECRET = 'rm0NMcIQ359N8iW6j2FQOuObRssiNslRP67Uza0YAxuhBzmTI6SD17haGKWr8lYe'
OAUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

def get_access_token():
    response = requests.get(OAUTH_URL, auth=HTTPBasicAuth(DARAJA_CONSUMER_KEY, DARAJA_CONSUMER_SECRET))
    if response.status_code == 200:
        access_token = response.json()['access_token']
        print("TOKEN RESPONSE:", response.text)
        return access_token
    else:
        return None
