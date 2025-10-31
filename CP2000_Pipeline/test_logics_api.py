"""
Test script to identify correct Logics API authentication method

Author: Hemalatha Yalamanchi
"""

import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv('LOGICS_API_KEY')

print("=" * 80)
print("🔍 LOGICS API AUTHENTICATION TEST")
print("=" * 80)
print(f"\n✅ API Key loaded: {api_key[:10]}...{api_key[-4:]}")

base_url = "https://tiparser-dev.onrender.com/case-data/api"
test_payload = {
    "ssn_last_4": "1234",
    "last_name": "TEST"
}

print(f"\n📍 Testing endpoint: {base_url}/case/match")
print(f"📦 Test payload: {test_payload}")

# Test 1: X-API-Key header (current method)
print("\n" + "=" * 80)
print("1️⃣  Testing: X-API-Key header (current method)")
print("=" * 80)
try:
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    response = requests.post(
        f"{base_url}/case/match",
        headers=headers,
        json=test_payload,
        timeout=10
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Headers: {dict(response.headers)}")
    print(f"   Response Body: {response.text[:500]}")
    if response.status_code == 200:
        print("   ✅ SUCCESS - This authentication method works!")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 2: Authorization Bearer token
print("\n" + "=" * 80)
print("2️⃣  Testing: Authorization Bearer token")
print("=" * 80)
try:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        f"{base_url}/case/match",
        headers=headers,
        json=test_payload,
        timeout=10
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Headers: {dict(response.headers)}")
    print(f"   Response Body: {response.text[:500]}")
    if response.status_code == 200:
        print("   ✅ SUCCESS - This authentication method works!")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 3: API key in query parameters
print("\n" + "=" * 80)
print("3️⃣  Testing: API key in query parameters")
print("=" * 80)
try:
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(
        f"{base_url}/case/match?apikey={api_key}",
        headers=headers,
        json=test_payload,
        timeout=10
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Headers: {dict(response.headers)}")
    print(f"   Response Body: {response.text[:500]}")
    if response.status_code == 200:
        print("   ✅ SUCCESS - This authentication method works!")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 4: API key in query parameters (alternate key name)
print("\n" + "=" * 80)
print("4️⃣  Testing: API key in query parameters (api_key)")
print("=" * 80)
try:
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(
        f"{base_url}/case/match?api_key={api_key}",
        headers=headers,
        json=test_payload,
        timeout=10
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Headers: {dict(response.headers)}")
    print(f"   Response Body: {response.text[:500]}")
    if response.status_code == 200:
        print("   ✅ SUCCESS - This authentication method works!")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 5: Basic Authentication
print("\n" + "=" * 80)
print("5️⃣  Testing: Basic Authentication")
print("=" * 80)
try:
    import base64
    credentials = f"{api_key}:".encode('utf-8')
    b64_credentials = base64.b64encode(credentials).decode('utf-8')
    headers = {
        "Authorization": f"Basic {b64_credentials}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        f"{base_url}/case/match",
        headers=headers,
        json=test_payload,
        timeout=10
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Headers: {dict(response.headers)}")
    print(f"   Response Body: {response.text[:500]}")
    if response.status_code == 200:
        print("   ✅ SUCCESS - This authentication method works!")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 6: Check health/status endpoint
print("\n" + "=" * 80)
print("6️⃣  Testing: Health/Status endpoint")
print("=" * 80)
for endpoint in ["/health", "/status", "/"]:
    try:
        print(f"\n   Trying: {base_url}{endpoint}")
        headers = {"X-API-Key": api_key}
        response = requests.get(
            f"{base_url}{endpoint}",
            headers=headers,
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        if response.status_code == 200:
            print(f"   ✅ Endpoint {endpoint} is accessible!")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

# Test 7: Check if server is even reachable
print("\n" + "=" * 80)
print("7️⃣  Testing: Server reachability (no auth)")
print("=" * 80)
try:
    response = requests.get(
        "https://tiparser-dev.onrender.com",
        timeout=10
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Server is reachable: ✅")
except Exception as e:
    print(f"   ❌ Server unreachable: {str(e)}")

# Test 8: Try GET instead of POST
print("\n" + "=" * 80)
print("8️⃣  Testing: GET request (instead of POST)")
print("=" * 80)
try:
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    response = requests.get(
        f"{base_url}/case/match",
        headers=headers,
        params=test_payload,
        timeout=10
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text[:500]}")
    if response.status_code == 200:
        print("   ✅ SUCCESS - GET method works!")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

print("\n" + "=" * 80)
print("🎯 SUMMARY")
print("=" * 80)
print("""
Review the results above to identify which authentication method returned:
- ✅ 200 (Success)
- ⚠️  401 (Unauthorized - wrong auth method)
- ⚠️  403 (Forbidden - insufficient permissions)
- ⚠️  404 (Not Found - wrong endpoint)
- ⚠️  500+ (Server error)

Next steps:
1. If any method succeeded (200), update logics_case_search.py to use that method
2. If all returned 403, contact Logics admin to verify:
   - API key is valid and active
   - IP address needs whitelisting
   - Account has proper permissions
3. If all returned 404, the endpoint URL might be incorrect
""")

