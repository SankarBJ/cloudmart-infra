# CloudMart AI — Marti Assistant ($0, Offline, No API Keys)

Zero-dependency AI upgrade: TF-IDF semantic search + grounded RAG chatbot
+ hybrid recommendations + trending + demand forecasting. Stdlib only —
runs on Flask slim image, EKS t3.medium, docker-compose. No AWS cost.

## New endpoints (backend/app.py)

| Endpoint | Purpose |
|---|---|
| `GET /api/ai/search?q=&top=` | Semantic product search (typo-tolerant, synonym + budget aware) |
| `POST /api/ai/chat {"message"}` | Grounded RAG: catalog + 5 store policies, cites sources |
| `GET /api/ai/recommend?product_id=&top=` | Hybrid recs (category + price + rating) with reasons |
| `GET /api/ai/trending?top=` | rating × log(reviews) ranking |
| `GET /api/ai/forecast/<id>` | Explainable demand heuristic + reorder flag |

## Files

- `app/backend/ai_core.py` — tokenize, synonyms, store policies
- `app/backend/ai_engine.py` — TF-IDF index, search, recommend, trending, forecast
- `app/backend/ai_chat.py` — grounded intents (greeting, policies, trending, product RAG)
- `app/frontend/ai-chat.html` — Marti chat UI (`/ai-chat`)
- `tests/test_ai_engine.py` — 9 tests, all passing

## Frontend wiring

- `shared.js` nav: `✨ Marti AI` link
- `index.html`: AI re-rank on `?search=` with banner + fallback; seller rows get
  `📈 Forecast` button calling `/api/ai/forecast`
- `product.html`: `✨ Frequently bought together` from `/api/ai/recommend`

## Try it (local)

```
cd app && docker compose up -d --build
curl "http://localhost:8080/api/ai/search?q=wireless%20headphones%20under%20100"
curl -X POST http://localhost:8080/api/ai/chat -H "Content-Type: application/json" -d "{\"message\":\"gift for coder\"}"
curl "http://localhost:8080/api/ai/recommend?product_id=3"
curl "http://localhost:8080/api/ai/trending?top=3"
curl "http://localhost:8080/api/ai/forecast/3"
python -m pytest tests/test_ai_engine.py -v
```

## Demo script (2 min)

1. Open `/ai-chat`, click chip `headphones under $100` → cites product sources.
2. Search `gift for coder` in header → AI banner + re-ranked grid.
3. Open any `/product?id=3` → recommendations with reasons.
4. Seller Central → `📈 Forecast` → reorder alert.
5. Ask `return policy` → grounded policy citation.

## Upgrade path (later, optional)

- Swap TF-IDF → sentence-transformers + FAISS/pgvector (needs image + RAM bump)
- Swap rules → LLM (Bedrock/Ollama) but KEEP citation guardrails
- Log chat feedback → fine-tune synonyms weekly
