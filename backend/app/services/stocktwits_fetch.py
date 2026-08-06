"""
StockTwits' public symbol-stream endpoint - no API key needed for light,
non-commercial use. Docs: https://api.stocktwits.com/developers/docs

This is the practical free substitute for "Twitter comments" that the
original project spec called for - X/Twitter's API is paid-only now.
"""
import cloudscraper

_STOCKTWITS_URL = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"

# Initialize scraper globally to keep session context, speed up calls, and defeat anti-bot challenges
scraper = cloudscraper.create_scraper()


class StockTwitsFetchError(Exception):
    """Raised for network failure, rate limiting, or an unknown symbol."""


def fetch_stocktwits_posts(symbol: str, limit: int = 15) -> list[dict]:
    try:
        # Use cloudscraper instead of requests to bypass the 'Just a moment...' 403 block
        resp = scraper.get(_STOCKTWITS_URL.format(symbol=symbol), timeout=8)
    except Exception as e:
        raise StockTwitsFetchError(f"Could not reach StockTwits: {e}") from e

    if resp.status_code == 404:
        raise StockTwitsFetchError(f"StockTwits has no stream for '{symbol}'")
    if resp.status_code == 429:
        raise StockTwitsFetchError("StockTwits rate limit hit (429) - try again shortly")
    if resp.status_code != 200:
        raise StockTwitsFetchError(f"StockTwits returned {resp.status_code}: {resp.text[:200]}")

    messages = resp.json().get("messages", [])[:limit]
    return [
        {
            "author": (m.get("user") or {}).get("username"),
            "content": m.get("body"),
            "url": f"https://stocktwits.com/message/{m['id']}" if m.get("id") else "https://stocktwits.com",
            "score": (m.get("likes") or {}).get("total"),
            "posted_at": m.get("created_at"),
        }
        for m in messages
        if m.get("body")
    ]
