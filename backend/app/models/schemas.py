"""
All request/response contracts for the API live here. Keeping schemas separate
from routers means the frontend team (or future-you) can read this one file
to know exactly what JSON shape to expect from every endpoint.
"""
from typing import List, Optional
from datetime import datetime
import json
import math
from pydantic import BaseModel, field_validator


def _nan_to_none(v):
    """yfinance returns float('nan') (not None) for fundamentals it has no
    value for - common on non-US tickers like NIFTY '.NS' symbols. NaN/Inf
    are valid Python floats but NOT valid JSON, and Starlette renders
    responses with json.dumps(allow_nan=False), so any NaN reaching a
    response raises 'Out of range float values are not JSON compliant' and
    500s the whole endpoint. Coercing to None here means 'no value', which
    is exactly what these Optional[float] fields already express."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


class TickerSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    region: str


class PricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoryResponse(BaseModel):
    symbol: str
    period: str
    interval: str
    candles: List[PricePoint]


class CompanyInfo(BaseModel):
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    currency: Optional[str] = None

    _clean_floats = field_validator(
        "market_cap", "pe_ratio", "eps", "dividend_yield",
        "fifty_two_week_high", "fifty_two_week_low",
        mode="before",
    )(_nan_to_none)


class IndicatorsResponse(BaseModel):
    symbol: str
    current_price: Optional[float] = None
    ema50: Optional[float] = None
    ema200: Optional[float] = None
    trend_signal: Optional[str] = None   # "bullish" | "bearish" | None
    golden_cross: Optional[bool] = None

    _clean_floats = field_validator(
        "current_price", "ema50", "ema200",
        mode="before",
    )(_nan_to_none)


class StockSummary(BaseModel):
    symbol: str
    company: CompanyInfo
    indicators: IndicatorsResponse


class LoginRequest(BaseModel):
    username: str
    passphrase: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    username: str
    has_passphrase: bool
    is_new: bool


class UserResponse(BaseModel):
    username: str
    has_passphrase: bool
    preferences: dict = {}


class PreferencesUpdate(BaseModel):
    preferences: dict


class WatchlistAddRequest(BaseModel):
    symbol: str


class WatchlistItemResponse(BaseModel):
    id: int
    symbol: str
    added_at: datetime

    model_config = {"from_attributes": True}  # lets us build this straight from an ORM row


class NewsArticleResponse(BaseModel):
    id: int
    symbol: str
    title: str
    url: str
    source: Optional[str] = None
    published_at: Optional[datetime] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    keywords: Optional[List[str]] = None

    model_config = {"from_attributes": True}

    @field_validator("keywords", mode="before")
    @classmethod
    def _parse_keywords(cls, v):
        # The DB column stores keywords as a JSON-encoded string; this lets
        # the schema accept either that string (from an ORM row) or an
        # already-parsed list (e.g. constructed directly in a test).
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v


class WatchlistSummaryItem(BaseModel):
    """One row of the watchlist dashboard. `summary` is None when that
    ticker's data couldn't be fetched this round - `error` explains why -
    so one bad ticker never breaks the whole dashboard response."""

    symbol: str
    summary: Optional[StockSummary] = None
    error: Optional[str] = None


class SocialPostResponse(BaseModel):
    id: int
    symbol: str
    source: str  # "reddit" | "stocktwits"
    author: Optional[str] = None
    content: str
    url: str
    score: Optional[int] = None
    posted_at: Optional[datetime] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    keywords: Optional[List[str]] = None

    model_config = {"from_attributes": True}

    @field_validator("keywords", mode="before")
    @classmethod
    def _parse_keywords(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v


class KnowledgeBaseBuildResponse(BaseModel):
    symbol: str
    documents_indexed: int


class KnowledgeBaseQueryResult(BaseModel):
    text: str
    doc_type: Optional[str] = None
    source: Optional[str] = None
    sentiment_label: Optional[str] = None
    distance: float

    @classmethod
    def from_raw(cls, raw: dict) -> "KnowledgeBaseQueryResult":
        """Builds this from a VectorStore.query() result dict, pulling the
        doc_type/source/sentiment_label up from Chroma's flat metadata dict."""
        metadata = raw.get("metadata") or {}
        return cls(
            text=raw["text"],
            doc_type=metadata.get("doc_type"),
            source=metadata.get("source"),
            sentiment_label=metadata.get("sentiment_label"),
            distance=raw["distance"],
        )


class AIInsightSource(BaseModel):
    doc_type: Optional[str] = None
    text: str


class AIInsightResponse(BaseModel):
    symbol: str
    provider: str
    insight: str
    sources: List[AIInsightSource]


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AIChatRequest(BaseModel):
    messages: List[ChatMessage]


class AIChatResponse(BaseModel):
    symbol: str
    provider: str
    reply: str
    sources: List[AIInsightSource]
