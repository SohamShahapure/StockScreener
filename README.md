> **Phase 11 is done** — per-user accounts (username login), a switch to the
> Groq LLM (much faster than local Ollama), concurrency/serialization
> optimizations, and full cloud deployment automation. See **[DEPLOYMENT.md](DEPLOYMENT.md)**
> for going live (Render + Vercel + Postgres) and `backend/README.md` for the
> Phase 11 backend notes. The section below documents the Phase 10 AI chat it
> builds on.

# Phase 10 — AI Investment Insight Generation (RAG + conversational chat)

Phase 10 turns the Phase 9 knowledge base into an **AI analyst you can talk
to**. From the watchlist, each ticker's **AI insight** button opens a chat:
it first generates a grounded, evidence-based investment summary, then lets
you keep asking follow-up questions about that stock — every answer
re-grounded in the retrieved financial context, not the model's pretrained
opinion.

## What it does

**Two endpoints** (`backend/app/routers/ai_insight.py`):

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/ai-insight/{symbol}` | Initial insight. Rebuilds the KB, retrieves context across the 4 categories, returns a structured summary + its sources. |
| POST | `/api/ai-insight/{symbol}/chat` | Follow-up Q&A. Takes the running conversation, re-grounds it in the (already-built) KB, returns the next reply. |

Both:
1. Retrieve the most relevant documents across four categories —
   **fundamentals, technical (EMA50/EMA200), recent news, public sentiment**.
2. Prompt an LLM — **Claude or Ollama**, chosen via `LLM_PROVIDER` — through
   LangChain, instructed to reason **only** over the retrieved context and to
   say "no data available" rather than guess when a category is empty.
3. Return the exact `sources` used, so the analysis is checkable, not a black
   box. The chat UI shows these under a "Grounded in N sources" toggle.

The initial insight uses a rigid 5-section prompt (the five dimensions
below); follow-ups drop the structure but keep the same grounding rules, so
the conversation stays evidence-based no matter where it goes. Braces and
punctuation in user questions or news text can't break the prompt — chat
messages are passed as LangChain message objects, not string templates.

**The five dimensions evaluated:** company fundamentals · EMA 50 & 200 trend
· recent financial news · public market sentiment · overall market outlook.

## Frontend

The watchlist "AI insight" button (`components/WatchlistCard.tsx`) is now
**live** and opens `components/AIInsightChat.tsx` — a modal chatbot:
- On open it fires the initial insight and streams in the structured summary.
- Suggested follow-up chips, then a free-text composer for anything else.
- Per-message "Grounded in N sources" disclosure.
- Clear, actionable error states (e.g. Ollama not running → the backend's
  503 message surfaces verbatim), Escape / backdrop to close.

## Setup

### 1. Install the LangChain packages
```bash
cd backend
pip install -r requirements.txt
# adds: langchain-core==1.5.3, langchain-anthropic==1.5.3, langchain-ollama==1.1.0
```

### 2. Choose your LLM provider
Set `LLM_PROVIDER` in `backend/.env` to either `ollama` or `anthropic`.

**Option A — Ollama (fully local, no API key, no cost)**
```
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
```
Requires Ollama installed (https://ollama.com) and the model pulled once:
```bash
ollama pull llama3.1
ollama serve   # if not already running
```

**Option B — Claude (Anthropic API)**
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```
Get a key at https://console.anthropic.com.

`LLM_TEMPERATURE=0.1` (already set) keeps output factual and consistent
rather than creative — appropriate for financial analysis.

## Restart and verify
```bash
cd backend && uvicorn app.main:app --reload
```
```bash
# initial insight
curl -X POST http://localhost:8000/api/ai-insight/AAPL
# follow-up chat
curl -X POST http://localhost:8000/api/ai-insight/AAPL/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Is the EMA trend bullish?"}]}'
```
The **first** call after starting the backend is the slow one: it loads the
embedding model, builds the KB, and cold-loads the local LLM (~220s measured
on llama3.1 8B). Later calls are much faster (~50s). The frontend timeouts
(300s initial / 240s follow-up) are sized to cover that cold start so the UI
never aborts a request the backend is still working on.

## Tests
```bash
cd backend && pytest tests/test_ai_insight.py tests/test_ai_insight_router.py -v
```
11 tests, all offline — they use `FakeListChatModel` (LangChain's own test
double) instead of a real Claude/Ollama call, plus the fake-embedding +
ephemeral-Chroma pattern from Phase 9. This covers the full retrieve →
prompt → invoke → parse pipeline for **both** the initial insight and the
chat turns, and both error paths (vector store unavailable, LLM provider
unreachable). Full suite: `pytest tests/` — 79 pass (2 pre-existing
Windows-only migration teardown flakes excluded).

## Verified live
Ran end-to-end against a local Ollama (`llama3.1`) for AAPL:
- Initial insight → HTTP 200, `provider=ollama`, 12 grounded sources, full
  5-dimension structured analysis.
- Follow-up ("is the EMA trend bullish?") → HTTP 200, correctly grounded
  answer citing the 50/200-day EMAs from the retrieved technical context.

## Notes
- The system prompt forbids prior knowledge about the company and requires
  "no data available" over guessing — this is what makes it retrieval-
  *grounded* rather than "ask an LLM about a stock with extra steps."
- Every response returns the exact retrieved snippets in `sources` — useful
  for demos (show the analysis is checkable) and for sanity-checking
  retrieval quality independent of the LLM.
- Follow-up turns reuse the already-built KB (no rebuild), so only the first
  insight per symbol pays the yfinance/news refetch cost.
