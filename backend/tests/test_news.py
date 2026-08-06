"""
Mocks news_fetch.fetch_news_for_query so these tests never hit the real
NewsAPI (no key needed, no network, no burning the 100-req/day free quota).
Uses FastAPI's dependency_overrides to swap in an isolated in-memory DB,
same pattern as the CRUD tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.services import news_fetch

FAKE_ARTICLES = [
    {
        "title": "Apple unveils new chip lineup",
        "url": "https://example.com/article-1",
        "source": "Reuters",
        "published_at": "2026-07-20T10:00:00Z",
    },
    {
        "title": "Apple stock rises on earnings beat",
        "url": "https://example.com/article-2",
        "source": "Bloomberg",
        "published_at": "2026-07-21T09:00:00Z",
    },
]


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_news_endpoint_fetches_and_caches(client, monkeypatch):
    call_count = {"n": 0}

    def fake_fetch(query, page_size=8):
        call_count["n"] += 1
        return FAKE_ARTICLES

    monkeypatch.setattr(news_fetch, "fetch_news_for_query", fake_fetch)

    resp = client.get("/api/news/AAPL")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["symbol"] == "AAPL"
    assert call_count["n"] == 1

    # Second call within the TTL window should be served from the DB cache -
    # NOT hit "NewsAPI" again.
    resp2 = client.get("/api/news/AAPL")
    assert resp2.status_code == 200
    assert call_count["n"] == 1


def test_news_endpoint_surfaces_upstream_error_as_502(client, monkeypatch):
    def fake_fetch_error(query, page_size=8):
        raise news_fetch.NewsFetchError("NEWS_API_KEY is not set")

    monkeypatch.setattr(news_fetch, "fetch_news_for_query", fake_fetch_error)

    resp = client.get("/api/news/TSLA")
    assert resp.status_code == 502
    assert "NEWS_API_KEY" in resp.json()["detail"]


def test_save_news_dedupes_on_symbol_and_url():
    """Direct CRUD-level test: saving the same article twice for the same
    symbol must not create a duplicate row (symbol+url is unique)."""
    from app.db import crud, models
    from app.db.database import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    crud.save_news(session, "AAPL", FAKE_ARTICLES)
    crud.save_news(session, "AAPL", FAKE_ARTICLES)  # same articles again

    rows = session.query(models.NewsArticle).filter_by(symbol="AAPL").all()
    assert len(rows) == 2  # not 4 - duplicates were skipped

    session.close()
