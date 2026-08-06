from datetime import datetime, timezone

from app.db import models
from app.models.schemas import CompanyInfo, IndicatorsResponse
from app.services import kb_documents


def test_build_fundamentals_document_includes_key_facts():
    company = CompanyInfo(
        symbol="AAPL", name="Apple Inc.", sector="Technology", industry="Consumer Electronics",
        market_cap=3_000_000_000_000, pe_ratio=28.5, eps=6.1, dividend_yield=0.005,
        fifty_two_week_high=240.0, fifty_two_week_low=160.0, currency="USD",
    )
    doc = kb_documents.build_fundamentals_document("AAPL", company)

    assert doc["id"] == "AAPL:fundamentals"
    assert "Apple Inc." in doc["text"]
    assert "Technology" in doc["text"]
    assert doc["metadata"]["symbol"] == "AAPL"
    assert doc["metadata"]["doc_type"] == "fundamentals"


def test_build_fundamentals_document_handles_missing_fields():
    company = CompanyInfo(symbol="ZZZ")
    doc = kb_documents.build_fundamentals_document("ZZZ", company)
    assert "unknown" in doc["text"]  # missing fields degrade gracefully, no crash


def test_build_technical_document_includes_trend():
    indicators = IndicatorsResponse(
        symbol="AAPL", current_price=200.0, ema50=195.0, ema200=180.0, trend_signal="bullish", golden_cross=True
    )
    doc = kb_documents.build_technical_document("AAPL", indicators)

    assert "200.0" in doc["text"]
    assert "bullish" in doc["text"]
    assert doc["metadata"]["trend_signal"] == "bullish"


def test_build_news_document_includes_sentiment_and_no_none_metadata():
    article = models.NewsArticle(
        id=1, symbol="AAPL", title="Apple beats earnings", url="https://x.com/1",
        source="Reuters", sentiment_label="positive",
        published_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )
    doc = kb_documents.build_news_document(article)

    assert "positive" in doc["text"]
    assert doc["id"] == "news:1"
    assert None not in doc["metadata"].values()  # Chroma rejects None metadata values


def test_build_news_document_handles_missing_sentiment():
    article = models.NewsArticle(id=2, symbol="AAPL", title="Some headline", url="https://x.com/2")
    doc = kb_documents.build_news_document(article)
    assert "Sentiment" not in doc["text"]  # no sentiment_label - shouldn't fabricate one
    assert None not in doc["metadata"].values()


def test_build_social_document_includes_source_and_content():
    post = models.SocialPost(
        id=5, symbol="AAPL", source="reddit", content="AAPL earnings looking strong this quarter",
        url="https://reddit.com/x", sentiment_label="positive",
    )
    doc = kb_documents.build_social_document(post)

    assert "Reddit" in doc["text"]
    assert "earnings looking strong" in doc["text"]
    assert doc["metadata"]["source"] == "reddit"
