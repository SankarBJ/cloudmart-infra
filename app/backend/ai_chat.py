"""Grounded RAG chatbot: answers ONLY from catalog + store policies."""
from ai_core import STORE_POLICIES


def _policy(pid):
    return next((p for p in STORE_POLICIES if p["id"] == pid), STORE_POLICIES[0])


def _cite_policy(pol):
    return {"type": "policy", "id": pol["id"], "title": pol["title"],
            "snippet": pol["text"][:160]}


def _cite_product(p, score, evidence):
    return {"type": "product", "id": p["id"], "title": p["name"],
            "price": float(p.get("price", 0)), "category": p.get("category"),
            "score": score, "evidence": evidence,
            "snippet": (p.get("description", "") or "")[:160]}


def chat_answer(engine, message):
    q = (message or "").strip()
    ql = q.lower()

    def ans(answer, cites, intent):
        return {"answer": answer, "citations": cites, "intent": intent,
                "grounded": True, "engine": "cloudmart-ai v1 (TF-IDF+rules, offline, $0)",
                "disclaimer": "Grounded in live catalog + store policies only."}

    if not q:
        return ans("Hello! Ask me to find products, compare, track orders, or explain policies.", [], "greeting")
    if len(ql.split()) <= 3 and any(w in ql for w in ["hello", "hi", "hey", "namaste", "vanakkam"]):
        return ans("Hello! I'm Marti, your CloudMart AI. Try: 'wireless headphones under $100', 'gift for coder', or 'track my order'.", [], "greeting")
    if any(w in ql for w in ["return", "refund", "exchange"]):
        pol = _policy("returns")
        return ans(pol["text"] + " Need a specific order? Open /orders.", [_cite_policy(pol)], "policy_returns")
    if any(w in ql for w in ["track", "where is my order", "delivery status", "shipment", "otp"]):
        pol = _policy("tracking")
        return ans(pol["text"] + " Share your order ID on /tracking for S2 OTP verification.", [_cite_policy(pol)], "policy_tracking")
    if any(w in ql for w in ["shipping", "delivery charge", "deliver to", "shipping policy"]):
        pol = _policy("shipping")
        return ans(pol["text"], [_cite_policy(pol)], "policy_shipping")
    if any(w in ql for w in ["payment", "upi", "cash on delivery", "netbanking", "payment method"]):
        pol = _policy("payment")
        return ans(pol["text"], [_cite_policy(pol)], "policy_payment")
    if any(w in ql for w in ["sell", "seller", "vendor", "publish"]):
        pol = _policy("seller")
        return ans(pol["text"], [_cite_policy(pol)], "policy_seller")
    if any(w in ql for w in ["trend", "bestseller", "popular", "top rated"]):
        t = engine.trending(top_k=3)
        names = ", ".join(x["product"]["name"] for x in t["items"])
        cites = [_cite_product(x["product"], x["score"], "trending") for x in t["items"]]
        return ans("Today's trending: " + names + ". Highly rated with 100+ reviews.", cites, "trending")

    hits = engine.semantic_search(q, top_k=3)
    if not hits or hits[0]["score"] < 0.05:
        return ans("No confident match in the catalog. Try a category (Electronics, Books, Fashion), a budget like 'under $50', or 'bestseller'.", [], "no_match")
    top = hits[0]
    msg = "Top pick: %s — $%.2f, %s stars (%s reviews)." % (
        top["product"]["name"], float(top["product"]["price"]),
        top["product"].get("rating"), top["product"].get("rating_count"))
    if len(hits) > 1:
        msg += " Alternatives: " + ", ".join(
            "%s ($%.2f)" % (h["product"]["name"], float(h["product"]["price"])) for h in hits[1:3]) + "."
    msg += " Why: matched %s, category %s." % (
        ", ".join(top["matched_terms"][:5]) or "semantic similarity", top["product"].get("category"))
    cites = [_cite_product(h["product"], h["score"], ",".join(h["matched_terms"][:4])) for h in hits]
    return ans(msg, cites, "product_rag")
