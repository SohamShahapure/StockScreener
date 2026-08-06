"""
Mocks stock_service.get_stock_summary (avoids needing yfinance) but uses a
real in-memory SQLite DB with actual news/social rows, and a real
VectorStore backed by an ephemeral Chroma client + fake embeddings - so
this proves the full build pipeline wiring end to end.
"""
import chromadb
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import crud
from app.db.database import Base
from app.models.schemas import CompanyInfo, IndicatorsResponse, StockSummary
from app.services import kb_builder, stock_service
from app.services.data_fetch import TickerNotFoundError
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
        client=client, embedding_function=FakeEmbeddingFunction(), collection_name=f"kb_{request.node.name}"
    )


def test_build_kb_indexes_fundamentals_technical_news_and_social(db_session, store, monkeypatch):
    def fake_summary(symbol, db):
        return StockSummary(
            symbol=symbol,
            company=CompanyInfo(symbol=symbol, name="Apple Inc.", sector="Technology"),
            indicators=IndicatorsResponse(symbol=symbol, current_price=200.0, trend_signal="bullish"),
        )

    monkeypatch.setattr(stock_service, "get_stock_summary", fake_summary)

    crud.save_news(
        db_session, "AAPL",
        [{"title": "Apple beats Q3 earnings estimates on strong iPhone sales", "url": "https://x.com/1"}],
    )
    crud.save_social_posts(
        db_session, "AAPL", "reddit",
        [{"content": "AAPL earnings look strong heading into next quarter", "url": "https://reddit.com/1"}],
    )

    result = kb_builder.build_knowledge_base_for_symbol("AAPL", db_session, store=store)

    # 1 fundamentals + 1 technical + 1 news + 1 reddit post = 4
    assert result["documents_indexed"] == 4
    assert store.count() == 4

    hits = store.query("AAPL", "earnings", top_k=10)
    assert len(hits) > 0
    assert all(h["metadata"]["symbol"] == "AAPL" for h in hits)


def test_build_kb_degrades_gracefully_when_price_data_unavailable(db_session, store, monkeypatch):
    def fake_summary_fails(symbol, db):
        raise TickerNotFoundError(f"No data for '{symbol}'")

    monkeypatch.setattr(stock_service, "get_stock_summary", fake_summary_fails)

    crud.save_news(
        db_session, "ZZZ",
        [{"title": "Some obscure company reports quarterly results today", "url": "https://x.com/2"}],
    )

    result = kb_builder.build_knowledge_base_for_symbol("ZZZ", db_session, store=store)

    # fundamentals/technical skipped, but the news doc still gets indexed
    assert result["documents_indexed"] == 1
    assert store.count() == 1


def test_build_kb_with_no_data_at_all_indexes_nothing(db_session, store, monkeypatch):
    def fake_summary_fails(symbol, db):
        raise TickerNotFoundError("nope")

    monkeypatch.setattr(stock_service, "get_stock_summary", fake_summary_fails)

    result = kb_builder.build_knowledge_base_for_symbol("NOPE", db_session, store=store)
    assert result["documents_indexed"] == 0
    assert store.count() == 0


def test_rebuilding_kb_overwrites_rather_than_duplicates(db_session, store, monkeypatch):
    def fake_summary(symbol, db):
        return StockSummary(
            symbol=symbol,
            company=CompanyInfo(symbol=symbol, name="Apple Inc."),
            indicators=IndicatorsResponse(symbol=symbol, current_price=200.0),
        )

    monkeypatch.setattr(stock_service, "get_stock_summary", fake_summary)

    kb_builder.build_knowledge_base_for_symbol("AAPL", db_session, store=store)
    first_count = store.count()
    kb_builder.build_knowledge_base_for_symbol("AAPL", db_session, store=store)
    second_count = store.count()

    assert first_count == second_count  # same doc ids -> upsert, not duplicate
