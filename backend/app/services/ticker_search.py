"""
Lightweight search over a static ticker list, so the frontend search bar
gets instant autocomplete without hitting Yahoo Finance on every keystroke.

To extend coverage later: replace data/tickers.json with a fuller dump
(e.g. all NSE-listed symbols or the full S&P 500 list) - nothing else
in this file needs to change.
"""
import json
from pathlib import Path
from typing import List

from app.models.schemas import TickerSearchResult

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "tickers.json"

with open(_DATA_PATH, "r", encoding="utf-8") as f:
    _TICKERS = json.load(f)


def search_tickers(query: str, limit: int = 10) -> List[TickerSearchResult]:
    q = query.strip().lower()
    if not q:
        return []

    scored = []
    for t in _TICKERS:
        symbol, name = t["symbol"].lower(), t["name"].lower()
        if q == symbol:
            score = 100
        elif symbol.startswith(q):
            score = 90
        elif q in symbol:
            score = 70
        elif name.startswith(q):
            score = 60
        elif q in name:
            score = 40
        else:
            continue
        scored.append((score, t))

    scored.sort(key=lambda pair: -pair[0])
    return [TickerSearchResult(**t) for _, t in scored[:limit]]


def get_company_name(symbol: str) -> str:
    """Best-effort lookup of a friendly company name for a symbol - news
    search relevance is much better on 'Apple Inc.' than on the raw 'AAPL'.
    Falls back to the symbol itself if it's not in our static list."""
    match = next((t for t in _TICKERS if t["symbol"].upper() == symbol.upper()), None)
    return match["name"] if match else symbol
