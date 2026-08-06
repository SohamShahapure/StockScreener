"""
All direct DB queries live here, so routers never touch SQLAlchemy sessions
directly - they call these functions instead. Keeps the persistence layer
swappable and testable in isolation.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db import models
from app.services import auth, nlp_pipeline


# --- Users (Phase 11) -----------------------------------------------------

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter_by(username=username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter_by(id=user_id).first()


def create_user(db: Session, username: str, passphrase: Optional[str] = None) -> models.User:
    user = models.User(
        username=username,
        passphrase_hash=auth.hash_passphrase(passphrase) if passphrase else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_user_passphrase(db: Session, user: models.User, passphrase: str) -> None:
    user.passphrase_hash = auth.hash_passphrase(passphrase)
    db.commit()


def update_user_preferences(db: Session, user: models.User, preferences: dict) -> models.User:
    user.preferences = json.dumps(preferences)
    db.commit()
    db.refresh(user)
    return user


# --- Watchlist (Phase 11: scoped per user) --------------------------------

def add_to_watchlist(db: Session, user_id: int, symbol: str) -> models.WatchlistItem:
    symbol = symbol.upper()
    existing = db.query(models.WatchlistItem).filter_by(user_id=user_id, symbol=symbol).first()
    if existing:
        return existing  # idempotent: adding twice is a no-op, not an error

    item = models.WatchlistItem(user_id=user_id, symbol=symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_from_watchlist(db: Session, user_id: int, symbol: str) -> bool:
    symbol = symbol.upper()
    item = db.query(models.WatchlistItem).filter_by(user_id=user_id, symbol=symbol).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def list_watchlist(db: Session, user_id: int) -> list[models.WatchlistItem]:
    return (
        db.query(models.WatchlistItem)
        .filter_by(user_id=user_id)
        .order_by(models.WatchlistItem.added_at.asc())
        .all()
    )


# --- Persistent fundamentals cache ----------------------------------------

def get_cached_payload(db: Session, symbol: str, data_type: str, ttl_seconds: int) -> Optional[dict]:
    symbol = symbol.upper()
    row = db.query(models.CachedQuote).filter_by(symbol=symbol, data_type=data_type).first()
    if not row:
        return None

    fetched_at = row.fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - fetched_at
    if age > timedelta(seconds=ttl_seconds):
        return None  # stale - caller should refetch and call set_cached_payload

    return json.loads(row.payload)


def set_cached_payload(db: Session, symbol: str, data_type: str, payload: dict) -> None:
    symbol = symbol.upper()
    row = db.query(models.CachedQuote).filter_by(symbol=symbol, data_type=data_type).first()
    payload_str = json.dumps(payload, default=str)  # default=str handles any stray non-JSON types

    if row:
        row.payload = payload_str
    else:
        row = models.CachedQuote(symbol=symbol, data_type=data_type, payload=payload_str)
        db.add(row)

    db.commit()


# --- News -----------------------------------------------------------------

def _parse_published_at(raw: Optional[str]):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def save_news(db: Session, symbol: str, articles: list[dict]) -> None:
    """Runs raw articles through the Phase 8 pipeline first - spam, near-
    duplicates, and too-short items are dropped here and never reach the
    DB. Survivors are saved with their cleaned title plus sentiment/keywords."""
    symbol = symbol.upper()
    processed = nlp_pipeline.process_items(articles, text_field="title")

    for a in processed:
        # symbol+url is unique - skip rather than duplicate if we've seen this article before
        exists = db.query(models.NewsArticle).filter_by(symbol=symbol, url=a["url"]).first()
        if exists:
            continue
        db.add(
            models.NewsArticle(
                symbol=symbol,
                title=a["title"],
                url=a["url"],
                source=a.get("source"),
                published_at=_parse_published_at(a.get("published_at")),
                sentiment_score=a.get("sentiment_score"),
                sentiment_label=a.get("sentiment_label"),
                keywords=json.dumps(a.get("keywords", [])),
            )
        )
    db.commit()


def get_latest_news(db: Session, symbol: str, limit: int = 10) -> list[models.NewsArticle]:
    symbol = symbol.upper()
    return (
        db.query(models.NewsArticle)
        .filter_by(symbol=symbol)
        .order_by(models.NewsArticle.fetched_at.desc())
        .limit(limit)
        .all()
    )


def get_cached_news(db: Session, symbol: str, ttl_seconds: int, limit: int = 10) -> Optional[list[models.NewsArticle]]:
    """Returns cached articles if we fetched this symbol's news recently
    enough, else None (signaling the caller should hit NewsAPI and re-save)."""
    rows = get_latest_news(db, symbol, limit)
    if not rows:
        return None

    most_recent = max(r.fetched_at for r in rows)
    if most_recent.tzinfo is None:
        most_recent = most_recent.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - most_recent
    if age > timedelta(seconds=ttl_seconds):
        return None

    return rows


def get_news_for_symbols(db: Session, symbols: list[str], limit: int = 20) -> list[models.NewsArticle]:
    """Merged, most-recent-first news across several tickers at once - what
    the watchlist dashboard shows instead of one feed per stock."""
    if not symbols:
        return []
    symbols = [s.upper() for s in symbols]
    return (
        db.query(models.NewsArticle)
        .filter(models.NewsArticle.symbol.in_(symbols))
        .order_by(models.NewsArticle.published_at.desc())
        .limit(limit)
        .all()
    )


# --- Social (Reddit / StockTwits) ------------------------------------------

def save_social_posts(db: Session, symbol: str, source: str, posts: list[dict]) -> None:
    """Same Phase 8 treatment as save_news - cleans, filters, dedupes, and
    enriches before anything reaches the DB. This is where the bulk of the
    filtering actually earns its keep, since scraped social posts run much
    noisier than newswire headlines."""
    symbol = symbol.upper()
    processed = nlp_pipeline.process_items(posts, text_field="content")

    for p in processed:
        exists = db.query(models.SocialPost).filter_by(symbol=symbol, source=source, url=p["url"]).first()
        if exists:
            continue
        db.add(
            models.SocialPost(
                symbol=symbol,
                source=source,
                author=p.get("author"),
                content=p["content"],
                url=p["url"],
                score=p.get("score"),
                posted_at=_parse_published_at(p.get("posted_at")),
                sentiment_score=p.get("sentiment_score"),
                sentiment_label=p.get("sentiment_label"),
                keywords=json.dumps(p.get("keywords", [])),
            )
        )
    db.commit()


def get_latest_social(db: Session, symbol: str, source: str, limit: int = 15) -> list[models.SocialPost]:
    symbol = symbol.upper()
    return (
        db.query(models.SocialPost)
        .filter_by(symbol=symbol, source=source)
        .order_by(models.SocialPost.fetched_at.desc())
        .limit(limit)
        .all()
    )


def get_cached_social(
    db: Session, symbol: str, source: str, ttl_seconds: int, limit: int = 15
) -> Optional[list[models.SocialPost]]:
    rows = get_latest_social(db, symbol, source, limit)
    if not rows:
        return None

    most_recent = max(r.fetched_at for r in rows)
    if most_recent.tzinfo is None:
        most_recent = most_recent.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - most_recent
    if age > timedelta(seconds=ttl_seconds):
        return None

    return rows
