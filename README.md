# TickerBoom — AI Stock Screener

A full-stack, AI-powered stock research dashboard. Search any US or Indian
(NSE) stock, read its candlestick chart and trend signals, track a personal
watchlist, and generate **evidence-based AI investment insights** grounded in
real financial data through Retrieval-Augmented Generation (RAG).

> **Live demo:** https://your-app.vercel.app  ·  **API:** https://stockscreener-api-safu.onrender.com

---

## What it does

- **Screener** — search by symbol or company, candlestick chart
  (`lightweight-charts`), company fundamentals, and EMA-50 / EMA-200 trend
  with a bullish/bearish "golden cross" read.
- **Watchlist** — sign in with a username to keep a personal watchlist that
  auto-refreshes live prices and merges news across all your tickers.
- **News & social sentiment** — recent financial news plus Reddit / StockTwits
  posts, each cleaned, de-duplicated, and sentiment-tagged.
- **AI Insight (the highlight)** — a chatbot that retrieves a stock's
  fundamentals, technicals, news, and sentiment from a vector knowledge base,
  then asks an LLM for a structured, source-cited analysis — and lets you ask
  follow-up questions. No hallucinated "the model's opinion"; every answer is
  grounded in retrieved context.

## Tech stack

| Layer | Tools |
|---|---|
| **Frontend** | Next.js 14 (App Router), TypeScript, TailwindCSS, lightweight-charts |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy, Pydantic |
| **Database** | PostgreSQL (SQLite for local dev) |
| **Market data** | yfinance (prices/fundamentals), NewsAPI, Reddit (PRAW) + StockTwits |
| **NLP** | VADER (sentiment), YAKE (keywords), custom cleaning/dedup pipeline |
| **RAG / AI** | ChromaDB vector store, all-MiniLM-L6-v2 (ONNX) embeddings, LangChain, Groq (Llama-3.3-70B) — also supports Claude & local Ollama |
| **Auth** | Lightweight username accounts with HMAC-signed tokens |
| **Deploy** | Frontend on Vercel · Backend + Postgres on Render |

## Using the live app

1. Open the live URL and **search a ticker** — try `AAPL`, `TSLA`, or
   `RELIANCE.NS` — to see its chart, fundamentals, and trend.
2. Go to **Watchlist** and **sign in with any username** (a passphrase is
   optional) to save stocks. New name = new account; your data persists.
3. On a watchlist stock, click **AI Insight** to generate a grounded analysis,
   then ask follow-up questions in the chat.

## Run it locally

Needs **Python 3.11+** and **Node.js 18+**.

**Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in keys (see below)
uvicorn app.main:app --reload    # http://localhost:8000  (docs at /docs)
```

**Frontend** (in a second terminal)
```bash
cd frontend
npm install
cp .env.local.example .env.local # NEXT_PUBLIC_API_URL defaults to localhost:8000
npm run dev                      # http://localhost:3000
```

### Optional API keys (`backend/.env`)
Everything except these works out of the box:
- `GROQ_API_KEY` — for AI insights (free at https://console.groq.com/keys). Set `LLM_PROVIDER=groq`.
- `NEWS_API_KEY` — news tab (free at https://newsapi.org).
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — Reddit sentiment (free "script" app at https://www.reddit.com/prefs/apps). StockTwits needs no key.

### Tests
```bash
cd backend && pytest tests/
```

## Deployment notes

- **Frontend → Vercel:** import the repo, set **Root Directory = `frontend`**,
  add `NEXT_PUBLIC_API_URL` = your backend URL.
- **Backend + DB → Render:** the [`render.yaml`](render.yaml) blueprint
  provisions the web service and a PostgreSQL database. Set secrets
  (`GROQ_API_KEY`, etc.) in the Render dashboard. `CORS_ORIGINS` accepts any
  `*.vercel.app` origin automatically.

---

Built as a portfolio project demonstrating full-stack development, financial
data engineering, an NLP pipeline, Retrieval-Augmented Generation, and modern
cloud deployment.
