"""
All yfinance calls are funneled through here. This buys us:
1. A single place to add caching, so we don't hammer Yahoo Finance's
   unofficial endpoint on every page refresh (it will start rate-limiting you).
2. A single place to normalize errors, so routers don't need to know
   anything about yfinance internals.
3. Browser impersonation + retries (Phase 11 deployment): Yahoo rate-limits
   plain datacenter requests (Render/Railway/etc.) far harder than
   browser-looking ones - especially the `.info`/quoteSummary endpoint, which
   needs a cookie+crumb handshake. A curl_cffi session impersonating Chrome
   gets past most of that; a short backoff-retry rides out transient 429s.
"""
import time

import pandas as pd
import yfinance as yf
from cachetools import TTLCache

from app.core.config import settings

_history_cache: TTLCache = TTLCache(maxsize=256, ttl=settings.CACHE_TTL_SECONDS)
_info_cache: TTLCache = TTLCache(maxsize=256, ttl=settings.CACHE_TTL_SECONDS)

_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 1.5  # multiplied by the attempt number each round


class TickerNotFoundError(Exception):
    """Raised when the symbol is genuinely invalid / has no data."""


class UpstreamDataError(Exception):
    """Raised when yfinance/Yahoo itself fails (network, rate limit, schema
    change) - i.e. the ticker might be perfectly valid, the fetch just failed."""


def _make_session():
    """A curl_cffi session impersonating Chrome, so Yahoo treats the request
    like a real browser instead of a blocked datacenter bot. Returns None if
    curl_cffi isn't available, in which case yfinance uses its own default."""
    try:
        from curl_cffi import requests as cffi_requests

        return cffi_requests.Session(impersonate="chrome")
    except Exception:
        return None


def _ticker(symbol: str) -> yf.Ticker:
    session = _make_session()
    return yf.Ticker(symbol, session=session) if session is not None else yf.Ticker(symbol)


def _is_rate_limited(err: Exception) -> bool:
    msg = str(err).lower()
    return "too many requests" in msg or "rate limit" in msg or "429" in msg


def get_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    key = (symbol, period, interval)
    if key in _history_cache:
        return _history_cache[key]

    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            df = _ticker(symbol).history(period=period, interval=interval)
            if df.empty:
                raise TickerNotFoundError(f"No price history found for '{symbol}'")
            _history_cache[key] = df
            return df
        except TickerNotFoundError:
            raise
        except Exception as e:  # noqa: BLE001 - normalized below
            last_err = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))

    raise UpstreamDataError(f"Failed to fetch price history for '{symbol}': {last_err}") from last_err


def get_info(symbol: str) -> dict:
    if symbol in _info_cache:
        return _info_cache[symbol]

    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            info = _ticker(symbol).info

            # yfinance returns a near-empty dict for a genuinely invalid ticker,
            # but a rate-limited response can also come back empty. Only treat it
            # as "not found" on the final attempt; otherwise retry.
            has_price = info.get("regularMarketPrice") or info.get("currentPrice")
            has_name = info.get("shortName") or info.get("longName")
            if has_price or has_name:
                _info_cache[symbol] = info
                return info
            raise UpstreamDataError(f"Empty company info for '{symbol}' (possibly rate limited)")
        except Exception as e:  # noqa: BLE001 - normalized below
            last_err = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))

    # Every attempt returned empty and nothing else has this symbol -> most
    # likely a real bad ticker, but under heavy rate-limiting it can be a false
    # negative, so the message leans on "rate limited" when that's the cause.
    if last_err and _is_rate_limited(last_err):
        raise UpstreamDataError(f"Failed to fetch company info for '{symbol}': {last_err}") from last_err
    if isinstance(last_err, UpstreamDataError) and "Empty company info" in str(last_err):
        raise TickerNotFoundError(f"No company info found for '{symbol}'") from last_err
    raise UpstreamDataError(f"Failed to fetch company info for '{symbol}': {last_err}") from last_err
