"""
Patches vector_store.get_vector_store (module reference, same pattern as
test_knowledge_base_router.py) and ai_insight._build_llm so the endpoint
runs the real router/service code with a fake vector store and a fake LLM -
no real embedding model download, no real API key, no network call.
"""
import chromadb
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.schemas import CompanyInfo, IndicatorsResponse, StockSummary
from app.services import ai_insight, stock_service, vector_store
from app.services.vector_store import VectorStore
from tests.fakes import FakeEmbeddingFunction


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    fake_store = VectorStore(
        client=chromadb.EphemeralClient(), embedding_function=FakeEmbeddingFunction(), collection_name="ai_router_test_kb"
    )
    monkeypatch.setattr(vector_store, "get_vector_store", lambda: fake_store)

    def fake_summary(symbol, db):
        return StockSummary(
            symbol=symbol,
            company=CompanyInfo(symbol=symbol, name="Apple Inc.", sector="Technology"),
            indicators=IndicatorsResponse(symbol=symbol, current_price=200.0, ema50=195.0, ema200=180.0, trend_signal="bullish"),
        )

    monkeypatch.setattr(stock_service, "get_stock_summary", fake_summary)

    fake_llm = FakeListChatModel(responses=["Fundamentals look solid. Overall outlook: cautiously positive."])
    monkeypatch.setattr(ai_insight, "_build_llm", lambda provider=None: fake_llm)

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_generate_insight_endpoint_returns_structured_response(client):
    resp = client.post("/api/ai-insight/AAPL")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "AAPL"
    assert "cautiously positive" in body["insight"]
    assert body["provider"] in ("groq", "anthropic", "ollama")
    assert isinstance(body["sources"], list)


def test_chat_endpoint_returns_grounded_reply(client):
    # Build the KB first (the initial insight call) so the follow-up has
    # something to retrieve and ground against.
    client.post("/api/ai-insight/AAPL")
    resp = client.post(
        "/api/ai-insight/AAPL/chat",
        json={"messages": [{"role": "user", "content": "Is the trend bullish?"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "AAPL"
    assert body["reply"]
    assert isinstance(body["sources"], list)


def test_chat_endpoint_rejects_empty_messages(client):
    resp = client.post("/api/ai-insight/AAPL/chat", json={"messages": []})
    assert resp.status_code == 422


def test_generate_insight_returns_503_when_llm_unreachable(monkeypatch):
    """Reproduces the real-world case: Ollama not running / Anthropic key
    missing. Must be a clean 503, not a raw 500."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fake_store = VectorStore(
        client=chromadb.EphemeralClient(), embedding_function=FakeEmbeddingFunction(), collection_name="ai_router_test_503"
    )
    monkeypatch.setattr(vector_store, "get_vector_store", lambda: fake_store)

    def fake_summary(symbol, db):
        return StockSummary(symbol=symbol, company=CompanyInfo(symbol=symbol, name="Apple Inc."), indicators=IndicatorsResponse(symbol=symbol, current_price=200.0))

    monkeypatch.setattr(stock_service, "get_stock_summary", fake_summary)

    def broken_llm_factory(provider=None):
        raise ai_insight.AIInsightError("Could not initialize the 'ollama' LLM provider - is Ollama running?")

    monkeypatch.setattr(ai_insight, "_build_llm", broken_llm_factory)
    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)
    resp = test_client.post("/api/ai-insight/AAPL")
    app.dependency_overrides.clear()

    assert resp.status_code == 503
    assert "Ollama" in resp.json()["detail"]
