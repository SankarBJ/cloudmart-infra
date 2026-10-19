"""Security helpers: rate limiting (in-memory), OTP hashing, input guards."""
import time
import hashlib
import secrets
from collections import defaultdict, deque

_hits = defaultdict(deque)

RATE_LIMITS = {
    "login": (5, 60),      # 5 attempts / 60s per IP
    "register": (5, 300),  # 5 / 5min per IP
    "otp": (6, 300),       # 6 OTP tries / 5min per order
    "chat": (30, 60),      # 30 chats / min per IP
}


def rate_ok(bucket, key, max_n=None, window=None):
    if bucket in RATE_LIMITS and max_n is None:
        max_n, window = RATE_LIMITS[bucket]
    now = time.time()
    q = _hits[(bucket, key)]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= max_n:
        return False, int(window - (now - q[0]))
    q.append(now)
    return True, 0


def hash_otp(otp):
    return hashlib.sha256(f"cm$otp${otp}".encode()).hexdigest()


def new_otp():
    return f"{secrets.randbelow(900000) + 100000}"


def check_password_strength(pw):
    if not pw or len(pw) < 6:
        return False, "Password must be at least 6 characters."
    return True, "ok"


def clean_str(s, limit=200):
    s = (s or "").strip()
    return s[:limit]
