"""
Tables:
- WatchlistItem : user's tracked tickers (single-user for now; a user_id
  column can be added later without breaking anything else, once auth exists)
- CachedQuote   : persistent cache of expensive/rate-limited yfinance
  responses (currently: company fundamentals), so a server restart doesn't
  throw away everything the in-memory TTLCache had
- NewsArticle   : news items (Phase 5), now with Phase 8's NLP-derived
  sentiment_score/sentiment_label/keywords columns
- SocialPost    : Reddit/StockTwits posts (Phase 7), with the same Phase 8
  NLP-derived columns
"""
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    """Phase 11: a lightweight account keyed by a unique username. The
    passphrase is optional (the user chose the low-friction identifier
    model) - when set, it's stored only as a salted PBKDF2 hash, never in
    plaintext. `preferences` is a free-form JSON blob for per-user UI state."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    passphrase_hash = Column(String, nullable=True)
    preferences = Column(Text, nullable=True)  # JSON-encoded dict
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # Phase 11: scopes the row to a user
    symbol = Column(String, nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Per-user uniqueness: two different users can each track AAPL, but a
    # single user can't add it twice.
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),)


class CachedQuote(Base):
    __tablename__ = "cached_quotes"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    data_type = Column(String, nullable=False)  # e.g. "info"
    payload = Column(Text, nullable=False)       # JSON-serialized dict
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("symbol", "data_type", name="uq_cache_symbol_type"),)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    source = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    # Phase 8: NLP-derived fields, populated before the row is ever saved.
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True)  # "positive" | "negative" | "neutral"
    keywords = Column(Text, nullable=True)  # JSON-encoded list[str]

    __table_args__ = (UniqueConstraint("symbol", "url", name="uq_news_symbol_url"),)


class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)  # "reddit" | "stocktwits"
    author = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    url = Column(String, nullable=False)
    score = Column(Integer, nullable=True)  # upvotes (Reddit) or likes (StockTwits)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    # Phase 8: NLP-derived fields, populated before the row is ever saved.
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True)
    keywords = Column(Text, nullable=True)  # JSON-encoded list[str]

    __table_args__ = (
        UniqueConstraint("symbol", "source", "url", name="uq_social_symbol_source_url"),
    )
