"""
Wraps NewsAPI.org's /v2/everything endpoint. Kept isolated here (like
data_fetch.py wraps yfinance) so swapping providers later - e.g. to Finnhub's
company-news endpoint - only touches this one file.

Get a free key at https://newsapi.org (Developer plan: 100 requests/day,
articles indexed up to ~1 month back - plenty for "latest news on a stock").
"""
import requests

from app.core.config import settings

_NEWSAPI_URL = "https://newsapi.org/v2/everything"


class NewsFetchError(Exception):
    """Raised for any failure to get news back - missing key, rate limit,
    network issue, or a malformed response. The router turns this into a
    clean 502 rather than a raw traceback."""


def fetch_news_for_query(query: str, page_size: int = 8) -> list[dict]:
    if not settings.NEWS_API_KEY:
        raise NewsFetchError(
            "NEWS_API_KEY is not set. Get a free key at https://newsapi.org and add it to .env"
        )

    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": settings.NEWS_API_KEY,
    }

    try:
        resp = requests.get(_NEWSAPI_URL, params=params, timeout=8)
    except requests.RequestException as e:
        raise NewsFetchError(f"Could not reach NewsAPI: {e}") from e

    if resp.status_code == 401:
        raise NewsFetchError("NewsAPI rejected the API key (401) - check NEWS_API_KEY in .env")
    if resp.status_code == 429:
        raise NewsFetchError("NewsAPI rate limit hit (429) - free tier allows 100 requests/day")
    if resp.status_code != 200:
        raise NewsFetchError(f"NewsAPI returned {resp.status_code}: {resp.text[:200]}")

    articles = resp.json().get("articles", [])
    return [
        {
            "title": a["title"],
            "url": a["url"],
            "source": (a.get("source") or {}).get("name"),
            "published_at": a.get("publishedAt"),
        }
        for a in articles
        if a.get("title") and a.get("url") and a["title"] != "[Removed]"
    ]
