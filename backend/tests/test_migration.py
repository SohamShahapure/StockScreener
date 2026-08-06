"""
Simulates exactly the real-world scenario: a stock_screener.db created by
an earlier phase (news_articles table exists, but without Phase 8's new
columns). Confirms init_db() patches it in place - existing rows survive,
new columns appear, ready to accept the new fields on the next write.
"""
import sqlite3
import tempfile
import os

from sqlalchemy import create_engine

from app.db.database import _add_missing_columns


def test_migration_adds_columns_to_pre_existing_table_without_losing_data():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        # Build an "old" schema by hand - news_articles exists, but with
        # only the columns Phase 5 originally shipped (no sentiment/keywords).
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE news_articles (
                id INTEGER PRIMARY KEY,
                symbol VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                url VARCHAR NOT NULL,
                source VARCHAR,
                published_at DATETIME,
                fetched_at DATETIME
            )
            """
        )
        conn.execute(
            "INSERT INTO news_articles (symbol, title, url, source) VALUES (?, ?, ?, ?)",
            ("AAPL", "Existing pre-Phase-8 article", "https://example.com/old", "Reuters"),
        )
        conn.commit()
        conn.close()

        # Point a real engine at this file and run the migration helper
        # against it directly (bypassing the module-level `engine` singleton,
        # which is already bound to the app's configured DATABASE_URL).
        import app.db.database as db_module

        test_engine = create_engine(f"sqlite:///{db_path}")
        original_engine = db_module.engine
        db_module.engine = test_engine
        try:
            _add_missing_columns()
        finally:
            db_module.engine = original_engine

        # Old data survived, new columns exist and are queryable/writable.
        conn = sqlite3.connect(db_path)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(news_articles)")}
        assert {"sentiment_score", "sentiment_label", "keywords"} <= cols

        row = conn.execute(
            "SELECT symbol, title, sentiment_score FROM news_articles WHERE url = ?",
            ("https://example.com/old",),
        ).fetchone()
        assert row == ("AAPL", "Existing pre-Phase-8 article", None)  # old row intact, new column defaults to NULL

        conn.execute(
            "UPDATE news_articles SET sentiment_score = ?, sentiment_label = ? WHERE url = ?",
            (0.62, "positive", "https://example.com/old"),
        )
        conn.commit()
        conn.close()
    finally:
        os.remove(db_path)


def test_migration_is_idempotent_when_columns_already_exist():
    """Running it twice (e.g. two app restarts) must not error."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE news_articles (id INTEGER PRIMARY KEY, symbol VARCHAR, title VARCHAR, url VARCHAR)"
        )
        conn.commit()
        conn.close()

        import app.db.database as db_module

        test_engine = create_engine(f"sqlite:///{db_path}")
        original_engine = db_module.engine
        db_module.engine = test_engine
        try:
            _add_missing_columns()
            _add_missing_columns()  # second call should be a safe no-op
        finally:
            db_module.engine = original_engine
    finally:
        os.remove(db_path)
