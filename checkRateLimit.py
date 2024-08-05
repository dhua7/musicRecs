import requests
import base64
from dotenv import load_dotenv
import os

# load .envfile
load_dotenv()

# Access Credentials
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

# Encode credentials
credentials = f"{client_id}:{client_secret}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

# Get access token
token_response = requests.post(
    'https://accounts.spotify.com/api/token',
    headers={
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    },
    data={'grant_type': 'client_credentials'}
)

# Extract access token
access_token = token_response.json().get('access_token')

# Use access token to make an API request
api_response = requests.get(
    'https://api.spotify.com/v1/tracks/{id}',  # Use a valid endpoint for testing
    headers={'Authorization': f'Bearer {access_token}'}
)

# Print response headers
print(api_response.headers)

# Extract and print rate limit information
rate_limit = api_response.headers.get('X-RateLimit-Limit')
rate_limit_remaining = api_response.headers.get('X-RateLimit-Remaining')
rate_limit_reset = api_response.headers.get('X-RateLimit-Reset')

print(f"Rate Limit: {rate_limit}")
print(f"Rate Limit Remaining: {rate_limit_remaining}")
print(f"Rate Limit Reset: {rate_limit_reset}")