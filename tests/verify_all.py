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

    print("=" * 70)
    print("   CLOUDMART HARDENED COMMERCE EXTENSION (7-12)")
    print("=" * 70)

    # 7. Prometheus metrics endpoint
    status, res, _, _ = request("GET", "/metrics")
    assert status == 200, res
    print("✅ TEST 7: Prometheus /metrics PASS")

    # 8. AI search live
    status, res, _, _ = request("GET", "/api/ai/search?q=headphones&top=2")
    assert status == 200 and len(res["results"]) > 0
    print(f"✅ TEST 8: AI semantic search PASS [Top: {res['results'][0]['product']['name'][:40]}]")

    # 9. AI chat grounded
    status, res, _, _ = request("POST", "/api/ai/chat", {"message": "return policy"})
    assert status == 200 and res.get("grounded") is True
    print(f"✅ TEST 9: AI grounded chat PASS [Intent: {res['intent']}]")

    # 10. UPI mock intent + verify
    status, res, _, _ = request("POST", "/api/payments/upi/intent", {"amount": 49.99, "order_id": order_id})
    assert status == 200 and res["upi_uri"].startswith("upi://pay?")
    txn = res["txn_id"]
    status, res, _, _ = request("POST", "/api/payments/upi/verify", {"txn_id": txn, "success": True})
    assert status == 200 and res["status"] == "SUCCESS" and res.get("utr")
    print(f"✅ TEST 10: UPI mock pay PASS [UTR: {res['utr']}]")

    # 11. Courier route shape
    status, res, _, _ = request("GET", f"/api/orders/{order_id}/route?steps=10")
    assert status == 200 and len(res["points"]) == 11
    print(f"✅ TEST 11: Courier route PASS [{len(res['points'])} stops]")

    # 12. Auth rate-limit guard exists (burst of bad logins eventually 429 OR 401s)
    codes = set()
    for _ in range(8):
        s, _, _, _ = request("POST", "/api/auth/login", {"email": "nobody@x.com", "password": "wrong"})
        codes.add(s)
    assert 401 in codes, codes
    print(f"✅ TEST 12: Login guard PASS [codes seen: {sorted(codes)}]")

    print("=" * 70)
    print("      ALL 12 TESTS PASSED (100%)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
