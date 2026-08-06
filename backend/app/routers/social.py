"""
Serves social sentiment for a ticker from Reddit or StockTwits, picked via
?source=. DB-cached the same way news is (Phase 5's pattern) - only re-hits
the live APIs when the cache is empty or stale.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import crud
from app.db.database import get_db
from app.models.schemas import SocialPostResponse
from app.services import reddit_fetch, stocktwits_fetch, ticker_search
from app.services.reddit_fetch import RedditFetchError
from app.services.stocktwits_fetch import StockTwitsFetchError

router = APIRouter(prefix="/api/social", tags=["social"])

_FETCH_ERRORS = (RedditFetchError, StockTwitsFetchError)


def _fetch_from_source(source: str, symbol: str) -> list[dict]:
    if source == "reddit":
        return reddit_fetch.fetch_reddit_posts(ticker_search.get_company_name(symbol))
    return stocktwits_fetch.fetch_stocktwits_posts(symbol)


@router.get("/{symbol}", response_model=list[SocialPostResponse])
def get_social(
    symbol: str,
    source: str = Query("reddit", pattern="^(reddit|stocktwits)$"),
    db: Session = Depends(get_db),
):
    symbol = symbol.upper()

    cached = crud.get_cached_social(db, symbol, source, settings.SOCIAL_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    try:
        posts = _fetch_from_source(source, symbol)
    except _FETCH_ERRORS as e:
        raise HTTPException(status_code=502, detail=str(e))

    crud.save_social_posts(db, symbol, source, posts)
    return crud.get_latest_social(db, symbol, source)
