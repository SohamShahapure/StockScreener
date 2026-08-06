"""
Add/remove/list is the persistence layer (Phase 3). This phase adds the two
endpoints that turn that into an actual "monitor multiple stocks" dashboard:
- /summary : current price + trend for every tracked ticker, in one call
- /news    : merged, most-recent-first news across every tracked ticker
"""
import math  # <-- Added to detect NaN and Infinity
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db import crud, models
from app.db.database import SessionLocal, get_db
from app.models.schemas import (
    NewsArticleResponse,
    WatchlistAddRequest,
    WatchlistItemResponse,
    WatchlistSummaryItem,
)
from app.services import news_fetch, stock_service, ticker_search
from app.services.data_fetch import TickerNotFoundError, UpstreamDataError

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def _clean_floats(obj):
    """Recursively converts non-JSON compliant floats (NaN, Inf) into None (null)."""
    if isinstance(obj, dict):
        return {k: _clean_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_floats(v) for v in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


@router.post("", response_model=WatchlistItemResponse, status_code=201)
def add_item(
    payload: WatchlistAddRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.add_to_watchlist(db, user.id, payload.symbol)


@router.get("", response_model=list[WatchlistItemResponse])
def list_items(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.list_watchlist(db, user.id)


@router.delete("/{symbol}", status_code=204)
def remove_item(
    symbol: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    removed = crud.remove_from_watchlist(db, user.id, symbol)
    if not removed:
        raise HTTPException(status_code=404, detail=f"'{symbol}' is not in the watchlist")


def _summary_for_symbol(symbol: str) -> dict:
    """Runs in its own thread with its own DB session - SQLAlchemy sessions
    aren't thread-safe, so a worker can't borrow the request's session."""
    worker_db = SessionLocal()
    try:
        summary = stock_service.get_stock_summary(symbol, worker_db)
        return _clean_floats(WatchlistSummaryItem(symbol=symbol, summary=summary).model_dump())
    except (TickerNotFoundError, UpstreamDataError) as e:
        return WatchlistSummaryItem(symbol=symbol, error=str(e)).model_dump()
    finally:
        worker_db.close()


@router.get("/summary")  # <-- Removed response_model here so we can clean raw dict outputs
def watchlist_summary(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """One row per tracked ticker - price, EMA50/200, trend. A failure on
    one ticker (delisted, rate-limited, typo'd symbol) never drops the
    others; it just comes back with `error` set instead of `summary`.

    Phase 11 optimization: yfinance calls are I/O-bound and release the GIL,
    so we fetch every ticker concurrently - an N-ticker watchlist now costs
    roughly one round-trip's wait instead of N sequential ones."""
    symbols = [item.symbol for item in crud.list_watchlist(db, user.id)]
    if not symbols:
        return []

    with ThreadPoolExecutor(max_workers=min(8, len(symbols))) as pool:
        return list(pool.map(_summary_for_symbol, symbols))


@router.get("/news", response_model=list[NewsArticleResponse])
def watchlist_news(
    limit: int = 20,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Merged news across every tracked ticker - what the watchlist page
    shows instead of making the user flip between per-stock news tabs."""
    items = crud.list_watchlist(db, user.id)
    symbols = [item.symbol for item in items]

    for symbol in symbols:
        cached = crud.get_cached_news(db, symbol, settings.NEWS_CACHE_TTL_SECONDS)
        if cached is None:
            try:
                fetched = news_fetch.fetch_news_for_query(ticker_search.get_company_name(symbol))
                crud.save_news(db, symbol, fetched)
            except news_fetch.NewsFetchError:
                continue  # this ticker just won't contribute fresh articles this round

    return crud.get_news_for_symbols(db, symbols, limit)
