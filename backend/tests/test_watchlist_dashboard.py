"""
Mocks stock_service and news_fetch so these tests never hit yfinance or
NewsAPI - same isolated in-memory DB + StaticPool pattern as test_news.py.
"""
import types

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_current_user
from app.db import crud
from app.db.database import Base, get_db
from app.main import app
from app.models.schemas import CompanyInfo, IndicatorsResponse, StockSummary
from app.services import news_fetch, stock_service
from app.services.data_fetch import TickerNotFoundError


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

    # Phase 11: every watchlist endpoint is now per-user. Seed a test user
    # and short-circuit the auth dependency to return it.
    setup_db = TestingSessionLocal()
    test_user_id = crud.create_user(setup_db, "tester").id
    setup_db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: types.SimpleNamespace(
        id=test_user_id, username="tester", passphrase_hash=None, preferences=None
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def _fake_summary(symbol: str) -> StockSummary:
    return StockSummary(
        symbol=symbol,
        company=CompanyInfo(symbol=symbol, name=f"{symbol} Inc."),
        indicators=IndicatorsResponse(symbol=symbol, current_price=100.0, trend_signal="bullish"),
    )


def test_watchlist_summary_returns_one_row_per_ticker(client, monkeypatch):
    client.post("/api/watchlist", json={"symbol": "AAPL"})
    client.post("/api/watchlist", json={"symbol": "TSLA"})

    def fake_get_summary(symbol, db):
        return _fake_summary(symbol)

    monkeypatch.setattr(stock_service, "get_stock_summary", fake_get_summary)

    resp = client.get("/api/watchlist/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert {row["symbol"] for row in body} == {"AAPL", "TSLA"}
    assert all(row["summary"] is not None and row["error"] is None for row in body)


def test_watchlist_summary_one_bad_ticker_does_not_break_the_rest(client, monkeypatch):
    client.post("/api/watchlist", json={"symbol": "AAPL"})
    client.post("/api/watchlist", json={"symbol": "ZZZFAKE"})

    def fake_get_summary(symbol, db):
        if symbol == "ZZZFAKE":
            raise TickerNotFoundError(f"No data for '{symbol}'")
        return _fake_summary(symbol)

    monkeypatch.setattr(stock_service, "get_stock_summary", fake_get_summary)

    resp = client.get("/api/watchlist/summary")
    assert resp.status_code == 200
    body = {row["symbol"]: row for row in resp.json()}

    assert body["AAPL"]["summary"] is not None
    assert body["AAPL"]["error"] is None
    assert body["ZZZFAKE"]["summary"] is None
    assert "No data" in body["ZZZFAKE"]["error"]


def test_watchlist_news_merges_across_tickers(client, monkeypatch):
    client.post("/api/watchlist", json={"symbol": "AAPL"})
    client.post("/api/watchlist", json={"symbol": "TSLA"})

    def fake_fetch(query, page_size=8):
        # Return one article whose title embeds the query so we can tell
        # AAPL's fetch apart from TSLA's fetch below.
        return [
            {
                "title": f"News about {query}",
                "url": f"https://example.com/{query.replace(' ', '-')}",
                "source": "Reuters",
                "published_at": "2026-07-20T10:00:00Z",
            }
        ]

    monkeypatch.setattr(news_fetch, "fetch_news_for_query", fake_fetch)

    resp = client.get("/api/watchlist/news")
    assert resp.status_code == 200
    body = resp.json()
    symbols_in_results = {a["symbol"] for a in body}
    assert symbols_in_results == {"AAPL", "TSLA"}


def test_watchlist_news_empty_when_no_watchlist(client):
    resp = client.get("/api/watchlist/news")
    assert resp.status_code == 200
    assert resp.json() == []
