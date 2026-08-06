"""
Uses FakeListChatModel (LangChain's own test double - no network, no API
key) for the LLM, and the same ephemeral-Chroma + FakeEmbeddingFunction
pattern from test_kb_builder.py for the vector store. This proves the full
retrieve -> prompt -> invoke -> parse pipeline works correctly; the actual
quality of Claude's or Ollama's real output isn't something a unit test
should be asserting on anyway.
"""
import chromadb
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import crud
from app.db.database import Base
from app.models.schemas import CompanyInfo, IndicatorsResponse, StockSummary
from app.services import ai_insight, stock_service
from app.services.vector_store import VectorStore
from tests.fakes import FakeEmbeddingFunction


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def store(request):
    client = chromadb.EphemeralClient()
    return VectorStore(
        client=client, embedding_function=FakeEmbeddingFunction(), collection_name=f"ai_{request.node.name}"
    )


def _fake_summary(symbol, db):
    return StockSummary(
        symbol=symbol,
        company=CompanyInfo(symbol=symbol, name="Apple Inc.", sector="Technology"),
        indicators=IndicatorsResponse(symbol=symbol, current_price=200.0, ema50=195.0, ema200=180.0, trend_signal="bullish"),
    )


def test_retrieve_context_returns_all_four_categories(db_session, store, monkeypatch):
    monkeypatch.setattr(stock_service, "get_stock_summary", _fake_summary)
    crud.save_news(db_session, "AAPL", [{"title": "Apple beats Q3 earnings estimates on strong iPhone sales", "url": "https://x.com/1"}])
    crud.save_social_posts(db_session, "AAPL", "reddit", [{"content": "AAPL earnings looking strong this quarter", "url": "https://reddit.com/1"}])

    context = ai_insight.retrieve_context("AAPL", db_session, store=store)

    assert set(context.keys()) == {"fundamentals", "technical", "news", "social"}
    assert len(context["fundamentals"]) > 0
    assert len(context["technical"]) > 0
    assert len(context["news"]) > 0
    assert len(context["social"]) > 0


def test_generate_insight_returns_structured_response_with_sources(db_session, store, monkeypatch):
    monkeypatch.setattr(stock_service, "get_stock_summary", _fake_summary)
    crud.save_news(db_session, "AAPL", [{"title": "Apple beats Q3 earnings estimates on strong iPhone sales", "url": "https://x.com/1"}])

    fake_llm = FakeListChatModel(responses=["1. Fundamentals: solid. 2. Technical: bullish. Summary: cautiously positive."])

    result = ai_insight.generate_insight("AAPL", db_session, store=store, llm=fake_llm)

    assert result["symbol"] == "AAPL"
    assert "cautiously positive" in result["insight"]
    assert len(result["sources"]) > 0
    assert all("doc_type" in s and "text" in s for s in result["sources"])


def test_generate_insight_degrades_gracefully_with_no_news_or_social(db_session, store, monkeypatch):
    """No news/social saved at all - the prompt should still get built (with
    'no data available' placeholders) and the chain should still run."""
    monkeypatch.setattr(stock_service, "get_stock_summary", _fake_summary)

    fake_llm = FakeListChatModel(responses=["Limited data available; fundamentals and technicals only."])
    result = ai_insight.generate_insight("AAPL", db_session, store=store, llm=fake_llm)

    assert result["symbol"] == "AAPL"
    assert "Limited data" in result["insight"]


def test_generate_insight_wraps_llm_failure_as_ai_insight_error(db_session, store, monkeypatch):
    monkeypatch.setattr(stock_service, "get_stock_summary", _fake_summary)

    def raising_llm(_prompt_value):
        # LangChain's coerce_to_runnable() wraps a plain callable in a
        # RunnableLambda automatically - simplest way to simulate "the LLM
        # provider is unreachable" without hand-rolling a Runnable subclass.
        raise ConnectionError("could not reach Ollama at localhost:11434")

    with pytest.raises(ai_insight.AIInsightError, match="LLM call failed"):
        ai_insight.generate_insight("AAPL", db_session, store=store, llm=raising_llm)


def test_unknown_provider_raises_clean_error():
    with pytest.raises(ai_insight.AIInsightError, match="Unknown LLM_PROVIDER"):
        ai_insight._build_llm(provider="chatgpt")


def test_chat_returns_grounded_reply_with_sources(db_session, store, monkeypatch):
    monkeypatch.setattr(stock_service, "get_stock_summary", _fake_summary)
    crud.save_news(db_session, "AAPL", [{"title": "Apple beats Q3 earnings estimates on strong iPhone sales", "url": "https://x.com/1"}])
    # chat() does NOT rebuild the KB, so populate it once up front.
    ai_insight.retrieve_context("AAPL", db_session, store=store)

    fake_llm = FakeListChatModel(responses=["The 50-day EMA sits above the 200-day EMA, which reads as bullish."])
    messages = [
        {"role": "assistant", "content": "Initial insight text."},
        {"role": "user", "content": "Is the trend bullish? Note: handles {braces} fine."},
    ]
    result = ai_insight.chat("AAPL", db_session, messages, store=store, llm=fake_llm)

    assert result["symbol"] == "AAPL"
    assert "bullish" in result["reply"]
    assert len(result["sources"]) > 0
    assert all("doc_type" in s and "text" in s for s in result["sources"])


def test_chat_wraps_llm_failure_as_ai_insight_error(db_session, store, monkeypatch):
    monkeypatch.setattr(stock_service, "get_stock_summary", _fake_summary)
    ai_insight.retrieve_context("AAPL", db_session, store=store)

    class _BoomLLM:
        def invoke(self, _messages):
            raise ConnectionError("could not reach Ollama at localhost:11434")

    with pytest.raises(ai_insight.AIInsightError, match="LLM call failed"):
        ai_insight.chat("AAPL", db_session, [{"role": "user", "content": "hi"}], store=store, llm=_BoomLLM())
