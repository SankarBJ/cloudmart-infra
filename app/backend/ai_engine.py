"""CloudMart AI engine: TF-IDF search + grounded RAG chat + recommendations."""
import math
import re
from collections import Counter
from ai_core import tokenize, expand_query, STORE_POLICIES


class CloudMartAIEngine:
    def __init__(self, products):
        self.products = products or []
        self.by_id = {p["id"]: p for p in self.products}
        self.doc_tokens, self.df, self.idf = {}, Counter(), {}
        self.doc_vectors, self.doc_norms = {}, {}
        self._build()

    def _text(self, p):
        return f"{p.get('name','')} {p.get('description','')} {p.get('category','')}"

    def _build(self):
        n = max(1, len(self.products))
        for p in self.products:
            toks = tokenize(self._text(p))
            self.doc_tokens[p["id"]] = toks
            for t in set(toks):
                self.df[t] += 1
        for t, df in self.df.items():
            self.idf[t] = math.log((n + 1) / (df + 1)) + 1.0
        for p in self.products:
            pid = p["id"]
            tf = Counter(self.doc_tokens[pid])
            tot = max(1, len(self.doc_tokens[pid]))
            vec = {t: (c / tot) * self.idf.get(t, 1.0) for t, c in tf.items()}
            self.doc_vectors[pid] = vec
            self.doc_norms[pid] = math.sqrt(sum(v * v for v in vec.values())) or 1.0

    def _qvec(self, query):
        toks = expand_query(tokenize(query))
        if not toks:
            return {}, 1.0
        tf = Counter(toks)
        tot = len(toks)
        max_idf = math.log(len(self.products) + 2)
        vec = {t: (c / tot) * self.idf.get(t, max_idf) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return vec, norm

    def _cos(self, qv, qn, pid):
        dv = self.doc_vectors.get(pid, {})
        dn = self.doc_norms.get(pid, 1.0)
        if not qv or not dv:
            return 0.0
        s = 0.0
        for t, q in qv.items():
            d = dv.get(t)
            if d:
                s += q * d
            elif len(t) >= 4:
                for dt, dv2 in dv.items():
                    if dt.startswith(t) or t.startswith(dt):
                        s += q * dv2 * 0.6
                        break
        return s / (qn * dn)

    @staticmethod
    def _price_hint(query):
        m = re.search(r"under\s*\$?\s*(\d+(?:\.\d+)?)", (query or "").lower())
        if m:
            return float(m.group(1))
        return None

    def semantic_search(self, query, top_k=5):
        qv, qn = self._qvec(query)
        hint = self._price_hint(query)
        out = []
        for p in self.products:
            s = self._cos(qv, qn, p["id"])
            if hint is not None and float(p.get("price", 0)) <= hint:
                s += 0.08
            s += float(p.get("rating", 0)) * 0.004
            matched = sorted(set(tokenize(query)) & set(self.doc_tokens.get(p["id"], [])))
            out.append({"product": p, "score": round(s, 4), "matched_terms": matched})
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[:top_k]

    def recommend(self, product_id, top_k=4):
        try:
            base = self.by_id.get(int(product_id))
        except Exception:
            base = None
        if not base:
            return self.trending(top_k=top_k)["items"]
        out = []
        for p in self.products:
            if p["id"] == base["id"]:
                continue
            s, reasons = 0.0, []
            if p.get("category") == base.get("category"):
                s += 0.5
                reasons.append("Same category: " + str(p.get("category")))
            try:
                bp, cp = float(base.get("price", 0)), float(p.get("price", 0))
                if bp > 0:
                    diff = abs(bp - cp) / bp
                    if diff <= 0.4:
                        s += (0.4 - diff) * 0.5
                        reasons.append("Similar price $%.2f" % cp)
            except Exception:
                pass
            try:
                s += float(p.get("rating", 0)) * 0.03
                reasons.append("Rated %s stars" % p.get("rating"))
            except Exception:
                pass
            out.append({"product": p, "score": round(s, 4), "reasons": reasons[:3]})
        out.sort(key=lambda x: x["score"], reverse=True)
        return out[:top_k]

    def trending(self, top_k=5):
        ranked = sorted(self.products, key=lambda p: (
            float(p.get("rating", 0)) * math.log(10 + int(p.get("rating_count", 0) or 0))), reverse=True)
        return {"items": [{"product": p, "score": float(p.get("rating", 0)),
                           "reasons": ["%s reviews" % p.get("rating_count", 0),
                                       "%s stars" % p.get("rating")]} for p in ranked[:top_k]],
                "strategy": "rating x log(review_count), deterministic"}

    def forecast(self, product_id):
        try:
            p = self.by_id.get(int(product_id))
        except Exception:
            p = None
        if not p:
            return {"error": "Product not found"}
        rating = float(p.get("rating", 4.0))
        reviews = int(p.get("rating_count", 0) or 0)
        stock = int(p.get("stock", 0) or 0)
        demand = round((rating / 5.0) * math.log(10 + reviews) * 1.2, 2)
        cover = round(stock / max(0.5, demand), 1)
        return {"product_id": p["id"], "product": p.get("name"),
                "predicted_daily_units": demand, "stock": stock,
                "days_of_cover": cover, "reorder_recommended": cover < 14,
                "model": "heuristic: (rating/5)*ln(10+reviews)*1.2"}
