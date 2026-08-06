"""
Both /api/stocks/{symbol}/summary and the new /api/watchlist/summary need
"fetch info + fetch indicators + combine" - this is that logic, written once.
Phase 2's whole point was a centralized data engine with no duplicated
logic across endpoints, so this is where that principle actually gets
enforced once a second consumer (the watchlist) shows up.
"""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import crud
from app.models.schemas import CompanyInfo, IndicatorsResponse, StockSummary
from app.services import data_fetch, indicators


def get_company_info(symbol: str, db: Session) -> CompanyInfo:
    """Checks the DB-backed cache first, falls back to yfinance."""
    raw = crud.get_cached_payload(db, symbol, "info", settings.DB_CACHE_TTL_SECONDS)
    if raw is None:
        raw = data_fetch.get_info(symbol)  # may raise TickerNotFoundError / UpstreamDataError
        crud.set_cached_payload(db, symbol, "info", raw)

    return CompanyInfo(
        symbol=symbol.upper(),
        name=raw.get("shortName") or raw.get("longName"),
        sector=raw.get("sector"),
        industry=raw.get("industry"),
        market_cap=raw.get("marketCap"),
        pe_ratio=raw.get("trailingPE"),
        eps=raw.get("trailingEps"),
        dividend_yield=raw.get("dividendYield"),
        fifty_two_week_high=raw.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=raw.get("fiftyTwoWeekLow"),
        currency=raw.get("currency"),
    )


def get_stock_indicators(symbol: str) -> IndicatorsResponse:
    # 2y of daily data comfortably covers a 200-day EMA warm-up period.
    df = data_fetch.get_history(symbol, period="2y", interval="1d")  # may raise same two errors
    result = indicators.compute_indicators(df)
    return IndicatorsResponse(symbol=symbol.upper(), **result)


def get_stock_summary(symbol: str, db: Session) -> StockSummary:
    company = get_company_info(symbol, db)
    ind = get_stock_indicators(symbol)
    return StockSummary(symbol=symbol.upper(), company=company, indicators=ind)
