# Stock Screener — Frontend (Phase 4, extended through Phase 8)

Next.js 14 (App Router) + TypeScript + TailwindCSS. Responsive from a small
phone screen up through a desktop monitor — bottom tab bar on mobile, top nav
on tablet/desktop.

Phase 9 (RAG knowledge base) was backend-only. Phase 10 (AI insight
generation) surfaces it in the UI: the watchlist "AI insight" button opens a
grounded chatbot (`components/AIInsightChat.tsx`) — an initial evidence-based
summary followed by free-form follow-up questions, every answer re-grounded
in the retrieved financial context.

## What's built
- **Screener (`/`)** — search bar with debounced autocomplete, candlestick
  chart (`lightweight-charts`), fundamentals card, EMA50/EMA200 + trend
  badges, "Add to watchlist" button. Right panel has two live tabs: News
  and Market Insights (Reddit/StockTwits toggle) for the searched stock.
- **Watchlist (`/watchlist`)** — a real personalized dashboard: pulls every
  tracked ticker's price/trend in one call, auto-refreshes every 30s, shows
  a live "Updated Xs ago" indicator plus a manual refresh button, and a
  merged news feed across every tracked ticker below the list. One bad
  ticker (delisted, rate-limited) shows an inline "unavailable" tag instead
  of breaking the rest of the dashboard.
- **Insights (`/insights`)** — search a ticker, see its Reddit/StockTwits
  sentiment directly (not tied to whatever's on the Screener page).

Both the News tab and Market Insights tab show a small sentiment tag
(green/red/gray) and keyword chips on each item (Phase 8) - the backend
cleans, filters spam, and sentiment-tags everything before it ever reaches
the frontend.

**Backend keys needed for full functionality** (see `backend/README.md`):
`NEWS_API_KEY` for the News tab, `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`
for the Reddit toggle. StockTwits needs no key. Any tab missing its key
shows a clear error message rather than failing silently.

## Prerequisites (fresh machine — install these first)

You need **Node.js** (which includes `npm`). If your machine has nothing on
it yet:

1. Go to **https://nodejs.org** and download the **LTS** version (not
   "Current") for your OS. Run the installer with defaults.
2. Verify it worked — open a terminal and run:
   ```bash
   node -v   # should print v20.x or v22.x
   npm -v    # should print 10.x
   ```
   If either command isn't found, restart your terminal (and on Windows,
   restart the machine) — this is almost always a PATH issue, not a real
   install failure.

That's it — no other global tools needed. Everything else (Next.js,
TailwindCSS, the chart library) installs locally into this project via
`npm install`, isolated from anything else on your machine.

## Setup
```bash
cd frontend
npm install
cp .env.local.example .env.local
```
`.env.local` just needs `NEXT_PUBLIC_API_URL` pointed at your running
backend — the default (`http://localhost:8000`) is correct if you're running
the backend locally with its default settings from Phase 1–3.

## Run
Make sure the **backend is running first** (see `backend/README.md` —
`uvicorn app.main:app --reload`), then in a separate terminal:
```bash
npm run dev
```
Open **http://localhost:3000**.

## Build for production
```bash
npm run build
npm run start
```

## Project structure
```
app/
├── layout.tsx           # fonts (next/font/google), global nav
├── globals.css          # Tailwind base + focus states + reduced-motion
├── page.tsx             # Screener (home)
├── watchlist/page.tsx
└── insights/page.tsx
components/
├── NavBar.tsx           # responsive: top bar (sm+) / bottom tabs (mobile)
├── SearchBar.tsx         # debounced autocomplete, keyboard-navigable
├── StockChart.tsx        # lightweight-charts candlestick wrapper
├── FundamentalsCard.tsx
├── IndicatorBadges.tsx   # price / EMA50 / EMA200 / trend
├── RightPanelTabs.tsx    # News / Market insights tabs
├── NewsPanel.tsx         # per-stock news feed - loading/error/empty states
├── NewsList.tsx          # shared article-list rendering (used by NewsPanel and the watchlist page)
├── SocialPanel.tsx       # Reddit/StockTwits toggle + posts for a symbol
├── SentimentTag.tsx      # sentiment badge + keyword chips (used by NewsList and SocialPanel)
├── WatchlistCard.tsx     # one row of the watchlist dashboard - price/trend/error/remove
└── TickerTape.tsx        # marquee on the empty state (signature visual touch)
lib/
├── api.ts               # typed fetch wrapper for the FastAPI backend
└── types.ts             # TypeScript types mirroring the backend's Pydantic schemas
```

## Design system (why it looks the way it does)
Built around a "trading terminal" identity without leaning on the generic
dark-mode-plus-neon look: a navy-ink background (`#0E1420`, not pure black),
a brass/gold accent (`#C9A227`) standing in for a brand color instead of the
usual terracotta or acid-green defaults, and real market-standard green/red
for gains/losses (that color coding is functional, not decorative — it's the
actual visual language traders read). Typography: Space Grotesk for
headings, Inter for body text, JetBrains Mono for anything numeric (prices,
EMAs, tickers) so figures align in neat columns — a real trading-terminal
convention, not decoration.

## Responsiveness notes
- Bottom tab bar under `sm` breakpoint (real thumb-reachable nav on phones),
  top bar above it.
- The Screener's chart/panel layout stacks vertically on mobile and moves
  to a 2/3 + 1/3 grid from `lg` up.
- All interactive elements have visible keyboard focus rings; animations
  respect `prefers-reduced-motion`.
- Chart uses `autoSize`, so it reflows on any screen/orientation change
  without a manual resize handler.

## Phase 10 — AI insight chat (done)
The watchlist "AI insight" button opens `AIInsightChat.tsx`, a modal
chatbot: it calls `POST /api/ai-insight/{symbol}` for an initial grounded
summary, then `POST /api/ai-insight/{symbol}/chat` for follow-up questions,
carrying the running conversation so the model keeps context. Each reply
shows a "Grounded in N sources" toggle, and the composer stays usable for
as long as you want to keep asking. Backend LLM is Claude or local Ollama
(`LLM_PROVIDER`); see `backend/README.md`.
