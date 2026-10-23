import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Note: This test script assumes an existing session or handles auth if possible. 
# For now, just checking endpoint response.
def test_endpoints():
    endpoints = ["/security/password-scans", "/security/url-scans", "/security/message-scans", "/security/deepfake-scans"]
    for ep in endpoints:
        print(f"Testing {ep}...")
        try:
            response = requests.get(f"{BASE_URL}{ep}")
            print(f"Status: {response.status_code}")
            # print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error: {e}")

test_endpoints()
