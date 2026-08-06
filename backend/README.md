# Stock Screener — Backend (Phases 1–9)

FastAPI backend serving stock search, historical prices, fundamentals, EMA
trend indicators, financial news, social sentiment (Reddit/StockTwits), an
NLP cleaning/enrichment pipeline, and a RAG knowledge base for downstream
AI insight generation (Phase 10).

## Structure
```
app/
├── main.py              # FastAPI app + CORS + router registration + DB init on startup
├── core/config.py       # env-driven settings (pydantic-settings)
├── models/schemas.py    # all request/response Pydantic models
├── db/
│   ├── database.py      # SQLAlchemy engine/session setup + lightweight auto-migration
│   ├── models.py        # WatchlistItem, CachedQuote, NewsArticle, SocialPost ORM tables
│   └── crud.py          # all direct DB queries; news/social saves run through the NLP pipeline first
├── services/
│   ├── data_fetch.py       # yfinance wrapper + in-memory TTL caching + error normalization
│   ├── indicators.py       # EMA50/EMA200 + trend signal math
│   ├── stock_service.py    # combines info+indicators into a StockSummary - shared across routers
│   ├── ticker_search.py    # static-list search/autocomplete + symbol->company name lookup
│   ├── news_fetch.py       # NewsAPI integration
│   ├── reddit_fetch.py     # PRAW (Reddit) integration
│   ├── stocktwits_fetch.py # StockTwits public API integration
│   ├── text_cleaning.py    # URL/HTML stripping + spam/ad/noise detection
│   ├── dedup.py            # near-duplicate detection (beyond URL-based uniqueness)
│   ├── sentiment.py        # VADER sentiment analysis
│   ├── topic_extraction.py # YAKE keyword/topic extraction
│   ├── nlp_pipeline.py     # orchestrates clean -> filter -> dedupe -> enrich (Phase 8)
│   ├── kb_documents.py     # turns fundamentals/technicals/news/social into RAG documents
│   ├── vector_store.py     # ChromaDB wrapper (dependency-injected client + embedding function)
│   └── kb_builder.py       # orchestrates building a symbol's knowledge base (Phase 9)
├── routers/
│   ├── stocks.py         # stock data endpoints (info DB-cached)
│   ├── watchlist.py      # add/list/remove + bulk /summary and merged /news dashboard endpoints
│   ├── news.py           # DB-cached NewsAPI integration
│   ├── social.py         # DB-cached Reddit/StockTwits integration
│   └── knowledge_base.py # RAG knowledge base build/query endpoints
└── data/tickers.json     # static ticker list for autocomplete
tests/                    # 70 tests total - see "Tests" section below
```

## Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Getting a free NewsAPI key (needed for `/api/news`)
1. Go to **https://newsapi.org/register**, sign up (free), verify your email.
2. Copy the API key from your account page into `.env` as `NEWS_API_KEY=`.
Free tier: 100 requests/day. Every other endpoint works without this key.

### Getting free Reddit credentials (needed for `/api/social?source=reddit`)
1. Go to **https://www.reddit.com/prefs/apps**, click "create app".
2. Type: **script**. Redirect URI: `http://localhost:8000` (required field, unused).
3. Copy the client ID (under the app name) and secret into `.env`:
   ```
   REDDIT_CLIENT_ID=...
   REDDIT_CLIENT_SECRET=...
   REDDIT_USER_AGENT=stock-screener-app by u/your_username
   ```
StockTwits needs no key - it's a public endpoint.

### Knowledge base (Phase 9) - one-time model download
The first call to `/api/kb/{symbol}/build` downloads the embedding model
(`all-MiniLM-L6-v2`, ~90MB) from Hugging Face. This needs internet **once**;
after that it's cached locally (`~/.cache` by default) and works offline.
If the download fails (no internet at that moment), the endpoint returns a
clear `503` explaining exactly that - not a crash - and retries cleanly on
the next call.

## Run
```bash
uvicorn app.main:app --reload
```
- API root: http://localhost:8000
- Docs: http://localhost:8000/docs
- First run creates `stock_screener.db` (SQLite) and, once the KB is built
  for any symbol, a `chroma_db/` directory - both automatic, no manual step.

### Existing database from an earlier phase?
Phase 8 added columns to the `news_articles`/`social_posts` tables. If you
have a `stock_screener.db` from before that, `database.py` auto-patches it
on startup (adds the missing columns without touching existing rows) -
just restart normally, nothing to do manually.

## Run tests
```bash
pytest tests/ -v
```
**70 tests, all offline** - no live yfinance/NewsAPI/Reddit/StockTwits
calls, and no real embedding-model download:
- Phases 1-3: EMA math, watchlist CRUD, DB-backed cache (13 tests)
- Phase 5: news endpoint, mocked NewsAPI (3 tests)
- Phase 6: bulk watchlist dashboard endpoints (4 tests)
- Phase 7: social endpoint, mocked Reddit/StockTwits (4 tests)
- Phase 8: text cleaning, dedup, sentiment, keyword extraction, full
  pipeline, and a migration test that simulates a pre-Phase-8 database (33 tests)
- Phase 9: vector store mechanics (via an ephemeral in-memory Chroma client
  + a deterministic fake embedding function), document construction, the
  full build pipeline, and the router including its 503 error path (21 tests)

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` `{"username","passphrase?"}` | Register-or-login; returns a signed token (Phase 11) |
| GET | `/api/auth/me` | Current user + preferences (requires token) |
| PUT | `/api/auth/preferences` `{"preferences":{...}}` | Save per-user UI preferences |
| GET | `/api/stocks/search?q=` | Autocomplete search by symbol or company name |
| GET | `/api/stocks/{symbol}/history?period=1y&interval=1d` | OHLCV candles for charting |
| GET | `/api/stocks/{symbol}/info` | Company fundamentals (DB-cached) |
| GET | `/api/stocks/{symbol}/indicators` | Current price, EMA50, EMA200, trend signal |
| GET | `/api/stocks/{symbol}/summary` | Combined info + indicators |
| POST | `/api/watchlist` `{"symbol": "AAPL"}` | Add a ticker (idempotent) |
| GET | `/api/watchlist` | List tracked tickers |
| DELETE | `/api/watchlist/{symbol}` | Remove a ticker (404 if not present) |
| GET | `/api/watchlist/summary` | Price + trend for every tracked ticker, in one call |
| GET | `/api/watchlist/news?limit=20` | Merged news across every tracked ticker |
| GET | `/api/news/{symbol}` | Recent news, DB-cached, cleaned + sentiment-tagged (Phase 8) |
| GET | `/api/social/{symbol}?source=reddit\|stocktwits` | Social posts, same cleaning/sentiment pipeline |
| POST | `/api/kb/{symbol}/build` | Build/refresh the RAG knowledge base for a symbol |
| GET | `/api/kb/{symbol}/query?q=&top_k=5` | Retrieve the most relevant indexed documents |
| POST | `/api/ai-insight/{symbol}` | Generate the initial grounded investment insight (Phase 10) |
| POST | `/api/ai-insight/{symbol}/chat` | Follow-up Q&A grounded in the symbol's KB (Phase 10) |

### Example calls
```bash
curl "http://localhost:8000/api/stocks/AAPL/summary"
curl -X POST http://localhost:8000/api/watchlist -H "Content-Type: application/json" -d '{"symbol":"AAPL"}'
curl http://localhost:8000/api/watchlist/summary
curl http://localhost:8000/api/news/AAPL
curl "http://localhost:8000/api/social/AAPL?source=stocktwits"

# Phase 9 - build then query the knowledge base
curl -X POST http://localhost:8000/api/kb/AAPL/build
curl "http://localhost:8000/api/kb/AAPL/query?q=is%20the%20trend%20bullish&top_k=5"
```

## The NLP pipeline (Phase 8), briefly
Every news article and social post runs through `nlp_pipeline.py` **before**
it's saved: clean text (strip URLs/HTML) -> drop spam/ads -> drop too-short
posts -> drop near-duplicates -> attach VADER sentiment + YAKE keywords.
Items that fail any filter are never stored - the DB only ever holds clean,
sentiment-tagged content.

## The RAG knowledge base (Phase 9), briefly
`kb_builder.build_knowledge_base_for_symbol(symbol, db)` pulls a symbol's
fundamentals, technicals, recent news, and recent social posts, turns each
into a short natural-language document (`kb_documents.py`), and embeds +
stores them in ChromaDB (`vector_store.py`). Re-building the same symbol
overwrites rather than duplicates (each document has a stable ID). If price
data is unavailable, the KB still builds from whatever news/social data
exists rather than failing outright.

`VectorStore` takes its Chroma client and embedding function as constructor
arguments rather than hardcoding them - production gets the real
persistent client + sentence-transformers model; tests inject an ephemeral
in-memory client + a fake embedding function, so all the storage/retrieval
logic is tested without needing the real model download.

## Two layers of caching (unchanged since Phase 3/5)
- In-memory TTLCache (`data_fetch.py`) - short-lived, process-local.
- DB-backed cache (`crud.py`, tables `cached_quotes`/`news_articles`/`social_posts`) -
  longer-lived, survives restarts.

## Phase 10 — AI Investment Insight Generation (done)
LangChain + an LLM (Claude or local Ollama, via `LLM_PROVIDER`) retrieves
context from the Phase 9 knowledge base to generate evidence-based
investment insights instead of relying on pretrained knowledge alone.
`services/ai_insight.py` exposes two entry points: `generate_insight()` (the
one-shot structured summary, rebuilds the KB) and `chat()` (grounded
multi-turn follow-up, reuses the KB). Both return the exact retrieved
`sources`. See `routers/ai_insight.py` for the two endpoints and the root
`README.md` for setup + live-verification notes.

## Phase 11 — Accounts, Groq, optimization & deployment (done)
- **Per-user accounts**: a lightweight username login (optional passphrase),
  HMAC-signed stateless tokens (`services/auth.py`), and a `users` table.
  Every `/api/watchlist/*` endpoint now requires a `Bearer` token and is
  scoped to that user - two users keep separate watchlists. See
  `routers/auth.py` and `core/deps.py`.
- **Groq LLM**: `LLM_PROVIDER=groq` (default) uses Groq's hosted API -
  dramatically faster than local Ollama (~sub-second follow-ups). Set
  `GROQ_API_KEY` in `.env`. `anthropic` and `ollama` still work.
- **Performance**: `/api/watchlist/summary` fetches every ticker
  concurrently (thread pool), and all responses use `ORJSONResponse`.
- **Postgres-ready**: `DATABASE_URL` auto-normalizes `postgres://` →
  `postgresql://` and uses `pool_pre_ping`. Point it at a managed Postgres
  for production; SQLite stays the local default.
- **Deployment**: see the repo-root `DEPLOYMENT.md` (Render + Vercel +
  Postgres), `render.yaml` blueprint, and `backend/Dockerfile`.
