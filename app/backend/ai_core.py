"""CloudMart AI core: tokenize + TF-IDF index (stdlib only, $0 cost)."""
import re
import math
from collections import Counter

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "with", "to", "in", "on",
    "is", "are", "i", "me", "my", "we", "you", "your", "it", "this",
    "that", "show", "find", "get", "give", "need", "want", "looking",
    "buy", "please", "under", "between", "cheap", "best", "good",
    "great", "top",
}

SYNONYMS = {
    "gift": ["gift", "present", "keyboard", "coding", "book", "coder", "developer", "programmer"],
    "coder": ["coder", "coding", "keyboard", "developer", "book", "data", "programming"],
    "developer": ["developer", "coding", "keyboard", "book", "coder", "programming"],
    "headphones": ["headset", "audio", "earphones", "anc", "noise", "wireless", "bluetooth"],
    "speaker": ["alexa", "smart", "audio", "echo"],
    "keyboard": ["mechanical", "typing", "coding", "gaming", "rgb"],
    "book": ["guide", "data", "architecture", "reading"],
    "bottle": ["flask", "insulated", "water", "steel"],
    "coffee": ["espresso", "barista", "maker"],
    "chair": ["cushion", "office", "ergonomic", "seat", "foam", "back"],
    "shirt": ["tshirt", "cotton", "fashion", "crewneck", "tee"],
    "backpack": ["bag", "hiking", "trail", "trekking", "travel"],
    "kindle": ["ereader", "reading", "display", "paperwhite"],
}

STORE_POLICIES = [
    {"id": "shipping", "title": "Shipping Policy",
     "text": "Free 2-day delivery over $25. Ships from Chennai Central Fulfillment Center with 5-stage tracking + S2 geofenced OTP within 50m."},
    {"id": "returns", "title": "Returns Policy",
     "text": "7-day easy returns. Refund within 48h of pickup. Items must be unused with tags."},
    {"id": "payment", "title": "Payment Methods",
     "text": "UPI, cards, netbanking and cash-on-delivery (simulated gateway in demo). Checkout is concurrency-safe with idempotency keys."},
    {"id": "tracking", "title": "Order Tracking",
     "text": "Track: Confirmed, Packed, In Transit, Out for Delivery (S2 cell shown), Delivered after 6-digit OTP."},
    {"id": "seller", "title": "Seller Central",
     "text": "Sellers publish via POST /api/seller/products with name, price, stock, category."},
]


def tokenize(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    toks = [t.strip("-") for t in text.split() if t.strip("-")]
    return [t for t in toks if t and t not in STOPWORDS]


def expand_query(tokens):
    expanded = list(tokens)
    for t in tokens:
        for key, syns in SYNONYMS.items():
            if t == key or t in syns:
                expanded.append(key)
                expanded.extend(syns)
    return expanded
