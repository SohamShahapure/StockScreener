"""
All stock-related REST endpoints. Business logic itself lives in
app/services/* - this file only handles HTTP concerns (validation,
status codes, wiring request -> service -> response schema).
"""
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.schemas import (
    CompanyInfo,
    HistoryResponse,
    IndicatorsResponse,
    PricePoint,
    StockSummary,
    TickerSearchResult,
)
from app.services import data_fetch, stock_service, ticker_search
from app.services.data_fetch import TickerNotFoundError, UpstreamDataError

router = APIRouter(prefix=settings.API_PREFIX, tags=["stocks"])


@router.get("/search", response_model=list[TickerSearchResult])
def search(q: str = Query(..., min_length=1, description="Ticker symbol or company name")):
    """Autocomplete search used by the frontend search bar."""
    return ticker_search.search_tickers(q)


@router.get("/{symbol}/history", response_model=HistoryResponse)
def history(
    symbol: str,
    period: str = Query(settings.DEFAULT_HISTORY_PERIOD, description="e.g. 1mo, 6mo, 1y, 5y, max"),
    interval: str = Query(settings.DEFAULT_HISTORY_INTERVAL, description="e.g. 1d, 1wk, 1mo"),
):
    """Historical OHLCV candles, used to render the price chart."""
    try:
        df = data_fetch.get_history(symbol, period=period, interval=interval)
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UpstreamDataError as e:
        raise HTTPException(status_code=502, detail=str(e))

    candles = []
    for idx, row in df.iterrows():
        ohlc = (row["Open"], row["High"], row["Low"], row["Close"])
        # yfinance occasionally yields rows with NaN OHLC (e.g. a market
        # holiday or an incomplete latest bar). A NaN is a valid float but
        # not valid JSON, and PricePoint's fields are required floats, so
        # such a row would 500 the response - skip it instead.
        if any(not math.isfinite(float(v)) for v in ohlc) or not math.isfinite(float(row["Volume"])):
            continue
        candles.append(
            PricePoint(
                date=str(idx.date()) if hasattr(idx, "date") else str(idx),
                open=round(float(row["Open"]), 2),
                high=round(float(row["High"]), 2),
                low=round(float(row["Low"]), 2),
                close=round(float(row["Close"]), 2),
                volume=int(row["Volume"]),
            )
        )
    return HistoryResponse(symbol=symbol.upper(), period=period, interval=interval, candles=candles)


@router.get("/{symbol}/info", response_model=CompanyInfo)
def info(symbol: str, db: Session = Depends(get_db)):
    """Company fundamentals: sector, market cap, P/E, EPS, dividend yield, 52w range."""
    try:
        return stock_service.get_company_info(symbol, db)
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UpstreamDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{symbol}/indicators", response_model=IndicatorsResponse)
def get_indicators(symbol: str):
    """Current price + EMA50/EMA200 + a bullish/bearish trend read."""
    try:
        return stock_service.get_stock_indicators(symbol)
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UpstreamDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{symbol}/summary", response_model=StockSummary)
def summary(symbol: str, db: Session = Depends(get_db)):
    """Convenience endpoint combining /info + /indicators for the watchlist view."""
    try:
        return stock_service.get_stock_summary(symbol, db)
    except TickerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UpstreamDataError as e:
        raise HTTPException(status_code=502, detail=str(e))
