"""
Uses its own in-memory SQLite engine (separate from the app's real DB file),
so these tests never touch stock_screener.db and run instantly, offline.
"""
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import crud
from app.db.database import Base


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def uid(db_session):
    """Phase 11: the watchlist is per-user, so tests need an owning user."""
    return crud.create_user(db_session, "tester").id


def test_add_and_list_watchlist(db_session, uid):
    crud.add_to_watchlist(db_session, uid, "aapl")
    crud.add_to_watchlist(db_session, uid, "tsla")

    items = crud.list_watchlist(db_session, uid)
    symbols = [i.symbol for i in items]

    assert symbols == ["AAPL", "TSLA"]  # uppercased, insertion order preserved


def test_add_is_idempotent(db_session, uid):
    crud.add_to_watchlist(db_session, uid, "AAPL")
    crud.add_to_watchlist(db_session, uid, "AAPL")  # adding twice should not duplicate

    items = crud.list_watchlist(db_session, uid)
    assert len(items) == 1


def test_remove_from_watchlist(db_session, uid):
    crud.add_to_watchlist(db_session, uid, "AAPL")

    removed = crud.remove_from_watchlist(db_session, uid, "aapl")
    assert removed is True
    assert crud.list_watchlist(db_session, uid) == []

    removed_again = crud.remove_from_watchlist(db_session, uid, "AAPL")
    assert removed_again is False  # already gone - should report False, not error


def test_watchlist_is_isolated_per_user(db_session):
    alice = crud.create_user(db_session, "alice").id
    bob = crud.create_user(db_session, "bob").id

    crud.add_to_watchlist(db_session, alice, "AAPL")
    crud.add_to_watchlist(db_session, bob, "TSLA")

    assert [i.symbol for i in crud.list_watchlist(db_session, alice)] == ["AAPL"]
    assert [i.symbol for i in crud.list_watchlist(db_session, bob)] == ["TSLA"]


def test_cache_set_and_get(db_session):
    payload = {"sector": "Technology", "trailingPE": 28.5}
    crud.set_cached_payload(db_session, "aapl", "info", payload)

    cached = crud.get_cached_payload(db_session, "AAPL", "info", ttl_seconds=300)
    assert cached == payload


def test_cache_expires_after_ttl(db_session):
    crud.set_cached_payload(db_session, "AAPL", "info", {"sector": "Technology"})

    time.sleep(1.1)
    # TTL of 1 second means our 1.1s-old entry should now read as stale
    cached = crud.get_cached_payload(db_session, "AAPL", "info", ttl_seconds=1)
    assert cached is None


def test_cache_miss_returns_none(db_session):
    assert crud.get_cached_payload(db_session, "NOPE", "info", ttl_seconds=300) is None
