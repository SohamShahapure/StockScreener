"""
All yfinance calls are funneled through here. Two things this buys us:
1. A single place to add caching, so we don't hammer Yahoo Finance's
   unofficial endpoint on every page refresh (it will start rate-limiting you).
2. A single place to normalize errors, so routers don't need to know
   anything about yfinance internals.
"""
import pandas as pd
import yfinance as yf
from cachetools import TTLCache

from app.core.config import settings

_history_cache: TTLCache = TTLCache(maxsize=256, ttl=settings.CACHE_TTL_SECONDS)
_info_cache: TTLCache = TTLCache(maxsize=256, ttl=settings.CACHE_TTL_SECONDS)


class TickerNotFoundError(Exception):
    """Raised when the symbol is genuinely invalid / has no data."""


class UpstreamDataError(Exception):
    """Raised when yfinance/Yahoo itself fails (network, rate limit, schema
    change) - i.e. the ticker might be perfectly valid, the fetch just failed."""


def get_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    key = (symbol, period, interval)
    if key in _history_cache:
        return _history_cache[key]

    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval)
    except Exception as e:
        raise UpstreamDataError(f"Failed to fetch price history for '{symbol}': {e}") from e

    if df.empty:
        raise TickerNotFoundError(f"No price history found for '{symbol}'")

    _history_cache[key] = df
    return df


def get_info(symbol: str) -> dict:
    if symbol in _info_cache:
        return _info_cache[symbol]

    try:
        info = yf.Ticker(symbol).info
    except Exception as e:
        raise UpstreamDataError(f"Failed to fetch company info for '{symbol}': {e}") from e

    # yfinance returns a near-empty dict for a genuinely invalid ticker rather
    # than raising - so we treat "no price fields at all" as not-found.
    has_price = info.get("regularMarketPrice") or info.get("currentPrice")
    has_name = info.get("shortName") or info.get("longName")
    if not has_price and not has_name:
        raise TickerNotFoundError(f"No company info found for '{symbol}'")

    _info_cache[symbol] = info
    return info
