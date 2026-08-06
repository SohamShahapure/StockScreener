"""
Central SQLAlchemy setup. Defaults to SQLite (zero setup, file-based) for
local dev. Point DATABASE_URL at a Postgres instance for production - nothing
else in the codebase needs to change, since all queries go through the ORM.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Managed Postgres providers (Render, Heroku, Railway) hand out URLs starting
# with the legacy `postgres://` scheme, but SQLAlchemy 2.x + psycopg2 expects
# `postgresql://`. Normalize it here so the same DATABASE_URL works verbatim
# from those dashboards without a manual edit.
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

# SQLite needs this flag because it otherwise refuses to share a connection
# across threads; Postgres doesn't need it (harmless to omit there).
connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

# pool_pre_ping avoids handing out a connection a managed Postgres has already
# dropped after an idle period (common on free tiers) - it silently reconnects.
engine = create_engine(_db_url, connect_args=connect_args, pool_pre_ping=not _db_url.startswith("sqlite"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a session, always closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables that don't exist yet, then patch any pre-existing
    tables with columns added by later phases. Called once on app startup."""
    from app.db import models  # noqa: F401 - import registers models on Base

    Base.metadata.create_all(bind=engine)  # only creates brand-new tables
    _add_missing_columns()  # patches tables that already existed on disk


# Columns added by Phase 8, keyed by table -> [(column_name, sql_type), ...].
# create_all() never ALTERs a table that already exists, so anyone with a
# stock_screener.db from before Phase 8 would otherwise hit "no such column"
# errors on the very next news/social fetch. A full migration tool (Alembic)
# is the real answer for production; for a SQLite dev DB, a couple of
# ALTER TABLE ADD COLUMN statements cover it without extra tooling.
_NEW_COLUMNS = {
    "news_articles": [
        ("sentiment_score", "FLOAT"),
        ("sentiment_label", "VARCHAR"),
        ("keywords", "TEXT"),
    ],
    "social_posts": [
        ("sentiment_score", "FLOAT"),
        ("sentiment_label", "VARCHAR"),
        ("keywords", "TEXT"),
    ],
    # Phase 11: watchlist rows are now per-user.
    "watchlist_items": [
        ("user_id", "INTEGER"),
    ],
}

def _add_missing_columns():
    if engine.dialect.name != "sqlite":
        return  # Postgres deployments start fresh - nothing to patch yet

    with engine.connect() as conn:
        for table, columns in _NEW_COLUMNS.items():
            existing_cols = {
                row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")
            }
            if not existing_cols:
                continue  # table doesn't exist yet - create_all() already made it, new columns included
            for col_name, col_type in columns:
                if col_name not in existing_cols:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
        _rebuild_watchlist_if_stale(conn)
        conn.commit()


def _rebuild_watchlist_if_stale(conn):
    """Phase 11 changed watchlist uniqueness from UNIQUE(symbol) to
    UNIQUE(user_id, symbol). The old single-column constraint was declared
    inline in CREATE TABLE, so SQLite backs it with an autoindex that
    DROP INDEX can't remove - the only way to shed it is to rebuild the
    table. We rename the old one, recreate it with the current schema, copy
    the rows over (pre-Phase-11 rows keep user_id = NULL, harmlessly
    invisible to every logged-in user), and drop the old table. No-op once
    the table already has the new-style constraint."""
    from app.db import models  # imported here to avoid a circular import at module load

    row = conn.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='watchlist_items'"
    ).fetchone()
    if not row or not row[0] or "uq_watchlist_user_symbol" in row[0]:
        return  # table missing (create_all handles it) or already migrated

    conn.exec_driver_sql("ALTER TABLE watchlist_items RENAME TO watchlist_items_old")
    # Renamed table keeps its explicit index names; drop them so recreating
    # the table (which reuses those names) doesn't collide.
    for idx in ("ix_watchlist_items_symbol", "ix_watchlist_items_id", "ix_watchlist_items_user_id"):
        conn.exec_driver_sql(f"DROP INDEX IF EXISTS {idx}")
    models.WatchlistItem.__table__.create(bind=conn)
    conn.exec_driver_sql(
        "INSERT INTO watchlist_items (id, user_id, symbol, added_at) "
        "SELECT id, user_id, symbol, added_at FROM watchlist_items_old"
    )
    conn.exec_driver_sql("DROP TABLE watchlist_items_old")
