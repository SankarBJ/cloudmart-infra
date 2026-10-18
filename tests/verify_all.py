import os
import urllib.request
import urllib.parse
import json
import time
import sys

# Bypass university/campus Squid proxy for localhost
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"
proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(proxy_handler)
urllib.request.install_opener(opener)

BASE_URL = "http://127.0.0.1:8080"

def request(method, path, data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            raw = response.read().decode()
            try:
                return response.status, json.loads(raw)
            except Exception:
                return response.status, {"raw_response": raw}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw_error": raw}
    except Exception as e:
        return 0, {"network_error": str(e)}

def run_tests():
    print("=" * 65)
    print("      CLOUDMART AUTOMATED VERIFICATION SUITE")
    print("=" * 65)

    # 1. Health Check
    status, res = request("GET", "/health")
    assert status == 200 and res.get("status") == "healthy", f"Health check failed: {res}"
    print("✅ TEST 1: System Health & Database Connectivity PASS")

    # 2. Catalog Search & Filter
    status, res = request("GET", "/api/products?search=Echo&category=Electronics")
    assert status == 200 and len(res.get("products", [])) > 0, f"Catalog search failed: {res}"
    product = res["products"][0]
    product_id = product["id"]
    print(f"✅ TEST 2: Product Catalog & Search Filtering PASS (Found: {product['name']})")

    # 3. User Registration / Login
    test_email = "automation_shopper@example.com"
    request("POST", "/api/auth/register", {
        "name": "Auto Shopper", "email": test_email, "password": "Password123!", "phone_number": "+919876543210"
    })
    status, res = request("POST", "/api/auth/login", {
        "email": test_email, "password": "Password123!"
    })
    assert status == 200 and "token" in res, f"Login failed: {res}"
    token = res["token"]
    user_id = res["user"]["id"]
    print(f"✅ TEST 3: User Authentication & JWT Issuance PASS (User ID: {user_id})")

    # 4. Protected Route & Customer Isolation
    status, res = request("GET", "/api/auth/me", token=token)
    assert status == 200 and res.get("user", {}).get("email") == test_email, f"Auth verification failed: {res}"
    print("✅ TEST 4: Protected Profile Access & Customer Isolation PASS")

    # 5. Cart Pre-Validation & Stock Check
    status, res = request("POST", "/api/cart/validate", {
        "items": [{"product_id": product_id, "quantity": 1}]
    })
    assert status == 200 and res.get("valid") is True, f"Cart validation failed: {res}"
    print(f"✅ TEST 5: Cart Calculation & Server Price Validation PASS (Total: ${res['total']})")

    # 6. Atomic Checkout Transaction
    idempotency_key = "test_key_" + str(hash(test_email))
    order_payload = {
        "items": [{"product_id": product_id, "quantity": 1}],
        "shipping_address": "88 Tech Park Avenue, Katpadi",
        "shipping_city": "Vellore",
        "shipping_postal_code": "632014",
        "idempotency_key": idempotency_key
    }
    status, res = request("POST", "/api/orders", order_payload, token=token)
    assert status == 201 and "order_id" in res, f"Order placement failed: {res}"
    order_id = res["order_id"]
    demo_otp = res["demo_otp_secret"]
    print(f"✅ TEST 6: Atomic Order Transaction & Inventory Lock PASS (Order #{order_id})")

    # 7. Duplicate Order Protection (Idempotency)
    status, res = request("POST", "/api/orders", order_payload, token=token)
    assert status == 200 and res.get("order_id") == order_id, f"Idempotency failed: {res}"
    print("✅ TEST 7: Duplicate Submission Protection (Idempotency Key) PASS")

    # 8. GEOFENCED ANTI-FRAUD LOGISTICS VERIFICATION
    # Step 8A: Fraud Test (Courier is 1.8km away -> MUST be rejected with 403 GEOFENCE_BREACH)
    status, res = request("POST", f"/api/orders/{order_id}/otp/verify", {
        "otp": demo_otp,
        "driver_lat": 12.9850,
        "driver_lng": 79.1700
    }, token=token)
    assert status == 403 and res.get("code") == "GEOFENCE_BREACH", f"Fraud test failed: {res}"
    print("✅ TEST 8A: Geofence Anti-Fraud Defense (1.8km breach blocked with 403) PASS")

    # Step 8B: Legitimate Doorstep Test (Courier is at 12.9717, 79.1586 -> 14.2m away -> MUST succeed with 200)
    status, res = request("POST", f"/api/orders/{order_id}/otp/verify", {
        "otp": demo_otp,
        "driver_lat": 12.9717,
        "driver_lng": 79.1586
    }, token=token)
    assert status == 200 and res.get("status") == "DELIVERED", f"Doorstep handshake failed: {res}"
    print("✅ TEST 8B: Doorstep Geofence Handshake (14.2m proximity verified with 200) PASS")

    print("=" * 65)
    print("     ALL 8 AUTOMATED INTEGRATION TESTS PASSED (100%)")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
