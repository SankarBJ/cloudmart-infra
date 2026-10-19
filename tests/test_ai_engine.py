"""Tests for CloudMart AI engine (stdlib-only, no services needed)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "backend"))
from ai_engine import CloudMartAIEngine
from ai_chat import chat_answer

PRODS = [
    {"id": 1, "name": "Echo Wave Smart Speaker", "description": "smart speaker alexa audio", "price": 49.99, "stock": 50, "category": "Electronics", "rating": 4.7, "rating_count": 342},
    {"id": 2, "name": "Kindle Paperwhite", "description": "reading display ereader", "price": 139.99, "stock": 35, "category": "Electronics", "rating": 4.8, "rating_count": 890},
    {"id": 3, "name": "CloudSonic Headphones", "description": "wireless bluetooth noise cancelling headphones", "price": 89.99, "stock": 40, "category": "Electronics", "rating": 4.6, "rating_count": 520},
    {"id": 4, "name": "Mechanical Keyboard", "description": "coding gaming rgb keyboard", "price": 69.99, "stock": 60, "category": "Electronics", "rating": 4.7, "rating_count": 610},
]


def test_semantic_search_finds_headphones():
    e = CloudMartAIEngine(PRODS)
    hits = e.semantic_search("wireless headphones", top_k=2)
    assert hits[0]["product"]["id"] == 3
    assert hits[0]["score"] > 0.1


def test_search_typo_tolerance():
    e = CloudMartAIEngine(PRODS)
    hits = e.semantic_search("headphon", top_k=2)
    assert hits[0]["product"]["id"] == 3


def test_budget_hint_boosts_cheap():
    e = CloudMartAIEngine(PRODS)
    hits = e.semantic_search("speaker under $50", top_k=2)
    assert hits[0]["product"]["id"] == 1


def test_recommend_same_category():
    e = CloudMartAIEngine(PRODS)
    recs = e.recommend(3, top_k=2)
    assert len(recs) == 2
    assert all(r["product"]["id"] != 3 for r in recs)
    assert all("reasons" in r for r in recs)


def test_trending_ordered():
    e = CloudMartAIEngine(PRODS)
    t = e.trending(top_k=2)
    assert len(t["items"]) == 2
    assert "strategy" in t


def test_forecast_shape():
    e = CloudMartAIEngine(PRODS)
    f = e.forecast(3)
    assert f["product_id"] == 3
    assert "predicted_daily_units" in f
    assert "reorder_recommended" in f


def test_chat_product_rag_grounded():
    e = CloudMartAIEngine(PRODS)
    r = chat_answer(e, "wireless headphones under $100")
    assert r["intent"] == "product_rag"
    assert r["grounded"] is True
    assert len(r["citations"]) > 0


def test_chat_policy_returns():
    e = CloudMartAIEngine(PRODS)
    r = chat_answer(e, "what is your return policy?")
    assert r["intent"] == "policy_returns"


def test_chat_gift_for_coder_is_product():
    e = CloudMartAIEngine(PRODS)
    r = chat_answer(e, "gift for coder")
    assert r["intent"] == "product_rag"
