"""Tests for backend hardening: security helpers, metrics, db fallback (no live DB)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "backend"))
os.environ["USE_DB"] = "off"
from security import rate_ok, hash_otp, new_otp, check_password_strength, clean_str
from metrics import observe, render_metrics
from db_layer import db_status


def test_otp_hash_roundtrip():
    o = new_otp()
    assert len(o) == 6 and o.isdigit()
    assert hash_otp(o) == hash_otp(o)
    assert hash_otp(o) != hash_otp("000000")


def test_password_policy():
    ok, _ = check_password_strength("short")
    assert not ok
    ok, _ = check_password_strength("Password123!")
    assert ok


def test_rate_limit_trips():
    key = "test-ip-unique-xyz"
    for _ in range(5):
        ok, _ = rate_ok("login", key)
        assert ok
    ok, retry = rate_ok("login", key)
    assert not ok and retry >= 0


def test_clean_str_truncates():
    assert clean_str("  hello  ") == "hello"
    assert len(clean_str("x" * 500, 10)) == 10


def test_metrics_render():
    observe("/api/test", 200, 12.5)
    observe("/api/test", 500, 30.0)
    out = render_metrics()
    assert "cloudmart_http_requests_total" in out
    assert "cloudmart_http_latency_ms_avg" in out


def test_db_off_mode():
    st = db_status()
    assert st["mode"] in ("memory-fallback", "unknown")
