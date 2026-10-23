import json
import urllib.request

BASE_URL = "http://127.0.0.1:8000"

def test_authenticated_flow():
    # 1. Register/Login to get a token
    print("Logging in...")
    login_req = urllib.request.Request(
        f"{BASE_URL}/auth/google-demo",
        data=json.dumps({"display_name": "Test User", "email": "test@example.com"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(login_req) as resp:
        data = json.loads(resp.read().decode())
    token = data["access_token"]
    user_id = data["user"]["id"]
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    print(f"Logged in. User ID: {user_id}")

    # 2. Run URL scan
    print("\nRunning URL scan...")
    url_req = urllib.request.Request(
        f"{BASE_URL}/security/analyze-url",
        data=json.dumps({"url": "https://example.com"}).encode(),
        headers=headers
    )
    with urllib.request.urlopen(url_req) as resp:
        assert resp.getcode() == 200
    print("URL scan successful.")

    # 3. Run Password scan
    print("\nRunning Password scan...")
    pwd_req = urllib.request.Request(
        f"{BASE_URL}/security/analyze-password",
        data=json.dumps({"password": "SecurePassword123!"}).encode(),
        headers=headers
    )
    with urllib.request.urlopen(pwd_req) as resp:
        assert resp.getcode() == 200
    print("Password scan successful.")

    # 4. Run Message scan
    print("\nRunning Message scan...")
    msg_req = urllib.request.Request(
        f"{BASE_URL}/security/analyze-message",
        data=json.dumps({"message": "Important meeting reminder at 3 PM."}).encode(),
        headers=headers
    )
    with urllib.request.urlopen(msg_req) as resp:
        assert resp.getcode() == 200
    print("Message scan successful.")

    # 5. Check history endpoints
    print("\nChecking history endpoints...")
    for endpoint, label in [("url-scans", "URL"), ("password-scans", "Password"), ("message-scans", "Message")]:
        h_req = urllib.request.Request(f"{BASE_URL}/security/{endpoint}", headers=headers)
        with urllib.request.urlopen(h_req) as resp:
            assert resp.getcode() == 200
            history = json.loads(resp.read().decode())
        print(f"{label} history count: {len(history)}")
        assert len(history) > 0, f"{label} history is empty!"

    print("\nAuthenticated scan and history verification PASSED!")

if __name__ == "__main__":
    test_authenticated_flow()

