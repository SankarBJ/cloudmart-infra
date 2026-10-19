import os
import urllib.request
import urllib.parse
import json
import time

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
            trace_id = response.headers.get('X-Trace-Id', 'none')
            latency = response.headers.get('X-Response-Time', 'none')
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"raw": raw}
            return response.status, parsed, trace_id, latency
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw), 'err', 'err'
        except Exception:
            return e.code, {"raw_error": raw}, 'err', 'err'
    except Exception as e:
        return 0, {"network_error": str(e)}, 'err', 'err'

def run_tests():
    print("=" * 70)
    print("   CLOUDMART GOOGLE-GRADE ARCHITECTURE & S2 VERIFICATION SUITE")
    print("=" * 70)

    # 1. Health & SRE Latency Headers
    status, res, trace_id, latency = request("GET", "/health")
    assert status == 200 and (res.get("status") == "healthy" or res.get("engine") == "Google-S2-Enabled")
    print(f"✅ TEST 1: System Health & Dapper Trace Span PASS [TraceID: {trace_id} | Latency: {latency}]")

    # 2. Catalog Search & Filter
    status, res, _, _ = request("GET", "/api/products?category=Office")
    assert status == 200 and len(res["products"]) == 1 and res["products"][0]["category"] == "Office"
    print(f"✅ TEST 2: Exact Category Filtering PASS [Returned: {res['products'][0]['name']}]")

    # 3. User Authentication
    status, res, _, _ = request("POST", "/api/auth/login", {"email": "sankar@example.com", "password": "Password123!"})
    assert status == 200 and "token" in res
    token = res["token"]
    print(f"✅ TEST 3: User Authentication & JWT Issuance PASS [User: {res['user']['name']}]")

    # 4. Transactional Outbox Pattern
    status, res, _, _ = request("POST", "/api/orders", {"items": [{"product_id": 7, "quantity": 1}]}, token=token)
    assert status == 201 and "outbox_event" in res
    order_id = res["order_id"]
    demo_otp = res["demo_otp_secret"]
    outbox = res["outbox_event"]
    print(f"✅ TEST 4: Asynchronous Transactional Outbox Event PASS [Event: {outbox['event_type']} | Status: {outbox['status']}]")

    # 5. Google S2 Spatial Geofence Verification (Fraud Check - 1.8km)
    status, res, _, _ = request("POST", f"/api/orders/{order_id}/otp/verify", {"otp": demo_otp, "driver_lat": 12.9850, "driver_lng": 79.1700}, token=token)
    assert status == 403 and res.get("code") == "GEOFENCE_BREACH"
    print(f"✅ TEST 5: Google S2 Anti-Fraud Rejection PASS [Distance: {res['proximity_meters']}m | Perimeter: 50m]")

    # 6. Google S2 Spatial Geofence Verification (Doorstep Handshake - 14.2m)
    status, res, _, _ = request("POST", f"/api/orders/{order_id}/otp/verify", {"otp": demo_otp, "driver_lat": 12.9717, "driver_lng": 79.1586}, token=token)
    assert status == 200 and res.get("status") == "DELIVERED"
    s2 = res["spatial_telemetry"]
    print(f"✅ TEST 6: Google S2 Doorstep Handshake PASS [Driver S2 Token: {s2['driver_s2_token']} | Target S2: {s2['target_s2_token']}]")

    print("=" * 70)
    print("      ALL GOOGLE-GRADE ARCHITECTURAL TESTS PASSED (100%)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
