"""Tests for UX Commerce Pack: courier sim + UPI intent shape (no network)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "backend"))
from courier_sim import courier_route


def test_route_shape():
    r = courier_route(7, steps=10)
    assert r["order_id"] == 7
    assert len(r["points"]) == 11
    assert r["points"][0]["step"] == 0
    assert "hub" in r and "doorstep" in r
    assert len(r["eta_minutes"]) == 11


def test_route_moves_toward_doorstep():
    r = courier_route(1, steps=12)
    import math
    def dist(p):
        return math.hypot(p["lat"] - r["doorstep"]["lat"], p["lng"] - r["doorstep"]["lng"])
    assert dist(r["points"][-1]) < dist(r["points"][0])


def test_upi_uri_format():
    amount, txn = 49.99, "TXN123456"
    uri = (f"upi://pay?pa=cloudmart@ybl&pn=CloudMart&tr={txn}"
           f"&am={amount:.2f}&cu=INR&tn=Order1")
    assert uri.startswith("upi://pay?")
    assert "pa=cloudmart@ybl" in uri and "cu=INR" in uri
