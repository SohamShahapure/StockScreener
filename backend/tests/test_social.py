"""
Mocks reddit_fetch.fetch_reddit_posts and stocktwits_fetch.fetch_stocktwits_posts
so these tests never hit the real APIs (no Reddit app credentials needed,
no StockTwits rate limit burned). Same isolated in-memory DB + StaticPool
pattern as test_news.py.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.services import reddit_fetch, stocktwits_fetch

FAKE_REDDIT_POSTS = [
    {
        "author": "trader123",
        "content": "AAPL earnings beat estimates, bullish going into next quarter",
        "url": "https://reddit.com/r/stocks/comments/abc123",
        "score": 245,
        "posted_at": "2026-07-20T10:00:00+00:00",
    }
]

FAKE_STOCKTWITS_POSTS = [
    {
        "author": "market_watcher",
        "content": "$AAPL breaking out above 200 EMA, watching closely",
        "url": "https://stocktwits.com/message/123456",
        "score": 12,
        "posted_at": "2026-07-21T09:00:00Z",
    }
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


def test_social_reddit_fetches_and_caches(client, monkeypatch):
    call_count = {"n": 0}

    def fake_fetch(query, limit=10):
        call_count["n"] += 1
        return FAKE_REDDIT_POSTS

    monkeypatch.setattr(reddit_fetch, "fetch_reddit_posts", fake_fetch)

    resp = client.get("/api/social/AAPL?source=reddit")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "AAPL"
    assert body[0]["source"] == "reddit"
    assert call_count["n"] == 1

    # Second call within the TTL window should be served from cache.
    resp2 = client.get("/api/social/AAPL?source=reddit")
    assert resp2.status_code == 200
    assert call_count["n"] == 1


def test_social_stocktwits_fetches_independently_of_reddit_cache(client, monkeypatch):
    monkeypatch.setattr(reddit_fetch, "fetch_reddit_posts", lambda query, limit=10: FAKE_REDDIT_POSTS)
    monkeypatch.setattr(
        stocktwits_fetch, "fetch_stocktwits_posts", lambda symbol, limit=15: FAKE_STOCKTWITS_POSTS
    )

    client.get("/api/social/AAPL?source=reddit")
    resp = client.get("/api/social/AAPL?source=stocktwits")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["source"] == "stocktwits"


def test_social_invalid_source_returns_422():
    from fastapi.testclient import TestClient as TC

    client = TC(app)
    resp = client.get("/api/social/AAPL?source=twitter")
    assert resp.status_code == 422  # Query pattern validation rejects it


def test_social_upstream_error_surfaces_as_502(client, monkeypatch):
    def fake_fetch_error(query, limit=10):
        raise reddit_fetch.RedditFetchError("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set")

    monkeypatch.setattr(reddit_fetch, "fetch_reddit_posts", fake_fetch_error)

    resp = client.get("/api/social/TSLA?source=reddit")
    assert resp.status_code == 502
    assert "REDDIT_CLIENT_ID" in resp.json()["detail"]
