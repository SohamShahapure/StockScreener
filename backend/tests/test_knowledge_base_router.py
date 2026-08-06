"""
Patches get_vector_store (module-level singleton) so the router uses an
ephemeral Chroma client + fake embeddings instead of trying to load the
real sentence-transformers model over the network.
"""
import chromadb
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.schemas import CompanyInfo, IndicatorsResponse, StockSummary
from app.services import stock_service, vector_store
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
        client=chromadb.EphemeralClient(), embedding_function=FakeEmbeddingFunction(), collection_name="router_test_kb"
    )
    monkeypatch.setattr(vector_store, "get_vector_store", lambda: fake_store)

    def fake_summary(symbol, db):
        return StockSummary(
            symbol=symbol,
            company=CompanyInfo(symbol=symbol, name="Apple Inc.", sector="Technology"),
            indicators=IndicatorsResponse(symbol=symbol, current_price=200.0, trend_signal="bullish"),
        )

    monkeypatch.setattr(stock_service, "get_stock_summary", fake_summary)

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_build_endpoint_returns_document_count(client):
    resp = client.post("/api/kb/AAPL/build")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "AAPL"
    assert body["documents_indexed"] >= 2  # at least fundamentals + technical


def test_query_endpoint_returns_relevant_results_after_build(client):
    client.post("/api/kb/AAPL/build")

    resp = client.get("/api/kb/AAPL/query", params={"q": "trading price trend"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) > 0
    assert all("distance" in r for r in body)


def test_query_before_build_returns_empty_list(client):
    resp = client.get("/api/kb/NEVERBUILT/query", params={"q": "anything"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_query_requires_nonempty_q_param(client):
    resp = client.get("/api/kb/AAPL/query", params={"q": ""})
    assert resp.status_code == 422


def test_build_returns_503_not_500_when_vector_store_unavailable(monkeypatch):
    """Reproduces the exact failure mode this sandbox actually hit: the
    embedding model can't load (no internet for the one-time download).
    Must come back as a clean 503, not a raw 500."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def broken_get_vector_store():
        raise vector_store.VectorStoreError(
            "Could not initialize the knowledge base. Check your internet connection and try again."
        )

    # kb_builder calls vector_store.get_vector_store() via module reference,
    # so patching it on the vector_store module is enough to reach both callers.
    monkeypatch.setattr(vector_store, "get_vector_store", broken_get_vector_store)
    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)
    resp = test_client.post("/api/kb/AAPL/build")
    app.dependency_overrides.clear()

    assert resp.status_code == 503
    assert "internet connection" in resp.json()["detail"]
