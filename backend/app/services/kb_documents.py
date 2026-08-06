"""
Turns the data Phases 2/5/7/8 already collect into short natural-language
"documents" ready for embedding - one document per fact/article/post, each
tagged with metadata so retrieval can filter by symbol and document type.

Chroma's metadata values must be str/int/float/bool - never None - so every
document builder here runs its metadata through `_clean_metadata`.
"""
from typing import Any

from app.db import models
from app.models.schemas import CompanyInfo, IndicatorsResponse


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Drops None values and stringifies anything Chroma can't store directly."""
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def build_fundamentals_document(symbol: str, company: CompanyInfo) -> dict:
    name = company.name or symbol
    text = (
        f"{name} ({symbol}) operates in the {company.sector or 'an unknown'} sector "
        f"({company.industry or 'unknown industry'}). "
        f"Market capitalization: {company.market_cap if company.market_cap is not None else 'unknown'}. "
        f"P/E ratio: {company.pe_ratio if company.pe_ratio is not None else 'unknown'}. "
        f"EPS: {company.eps if company.eps is not None else 'unknown'}. "
        f"Dividend yield: {company.dividend_yield if company.dividend_yield is not None else 'unknown'}. "
        f"52-week range: {company.fifty_two_week_low} to {company.fifty_two_week_high}."
    )
    return {
        "id": f"{symbol}:fundamentals",
        "text": text,
        "metadata": _clean_metadata(
            {"symbol": symbol, "doc_type": "fundamentals", "source": "yfinance"}
        ),
    }


def build_technical_document(symbol: str, indicators: IndicatorsResponse) -> dict:
    text = (
        f"{symbol} is currently trading at {indicators.current_price}. "
        f"The 50-day EMA is {indicators.ema50 if indicators.ema50 is not None else 'not yet available'} "
        f"and the 200-day EMA is {indicators.ema200 if indicators.ema200 is not None else 'not yet available'}. "
        f"Trend signal: {indicators.trend_signal or 'insufficient data for a trend read'}."
    )
    return {
        "id": f"{symbol}:technical",
        "text": text,
        "metadata": _clean_metadata(
            {
                "symbol": symbol,
                "doc_type": "technical",
                "source": "yfinance",
                "trend_signal": indicators.trend_signal,
            }
        ),
    }


def build_news_document(article: models.NewsArticle) -> dict:
    text = f"News ({article.source or 'unknown source'}): {article.title}"
    if article.sentiment_label:
        text += f" Sentiment: {article.sentiment_label}."

    return {
        "id": f"news:{article.id}",
        "text": text,
        "metadata": _clean_metadata(
            {
                "symbol": article.symbol,
                "doc_type": "news",
                "source": article.source,
                "sentiment_label": article.sentiment_label,
                "published_at": article.published_at.isoformat() if article.published_at else None,
            }
        ),
    }


def build_social_document(post: models.SocialPost) -> dict:
    text = f"{post.source.capitalize()} post: {post.content}"
    if post.sentiment_label:
        text += f" Sentiment: {post.sentiment_label}."

    return {
        "id": f"social:{post.id}",
        "text": text,
        "metadata": _clean_metadata(
            {
                "symbol": post.symbol,
                "doc_type": "social",
                "source": post.source,
                "sentiment_label": post.sentiment_label,
            }
        ),
    }
