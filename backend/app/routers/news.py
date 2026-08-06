"""
Serves recent news for a ticker. Checked against the DB cache (Phase 3's
NewsArticle table) first - only hits NewsAPI when the cache is empty or
stale, which matters a lot given NewsAPI's free tier is 100 requests/day.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import crud
from app.db.database import get_db
from app.models.schemas import NewsArticleResponse
from app.services import news_fetch, ticker_search

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/{symbol}", response_model=list[NewsArticleResponse])
def get_news(symbol: str, db: Session = Depends(get_db)):
    symbol = symbol.upper()

    cached = crud.get_cached_news(db, symbol, settings.NEWS_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    query = ticker_search.get_company_name(symbol)
    try:
        articles = news_fetch.fetch_news_for_query(query)
    except news_fetch.NewsFetchError as e:
        raise HTTPException(status_code=502, detail=str(e))

    crud.save_news(db, symbol, articles)
    return crud.get_latest_news(db, symbol)
