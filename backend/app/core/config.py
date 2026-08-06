"""
Centralized app configuration, loaded from environment variables / .env file.
Keeping this separate means every other module imports `settings` instead of
reading os.environ directly - one source of truth.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Stock Screener API"
    API_PREFIX: str = "/api/stocks"

    # Comma-free JSON list in .env, e.g. ["http://localhost:3000"]. In
    # production set this to your Vercel URL (Phase 11 deployment).
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Phase 11 auth: signs the login tokens. MUST be overridden in production
    # via the SECRET_KEY env var - anyone who knows it can mint valid tokens.
    SECRET_KEY: str = "dev-insecure-change-me-in-production"

    # How long (seconds) cached yfinance responses stay fresh before refetching.
    CACHE_TTL_SECONDS: int = 300

    # SQLite by default for zero-setup local dev. For production, point this at
    # a managed Postgres instance, e.g.:
    # postgresql://user:password@host:5432/stock_screener
    DATABASE_URL: str = "sqlite:///./stock_screener.db"

    # Persistent (DB-backed) cache TTL for company fundamentals - longer-lived
    # than the in-memory TTL since fundamentals change slowly and this cache
    # survives server restarts, unlike the in-memory one.
    DB_CACHE_TTL_SECONDS: int = 1800

    # Free key from https://newsapi.org (Developer plan: 100 requests/day).
    NEWS_API_KEY: str = ""
    NEWS_CACHE_TTL_SECONDS: int = 1800

    # Reddit (PRAW) - free "script" app from https://www.reddit.com/prefs/apps
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "stock-screener-app by u/yourusername"
    REDDIT_SUBREDDITS: str = "stocks,wallstreetbits,investing"

    # StockTwits' public symbol-stream endpoint needs no API key.
    SOCIAL_CACHE_TTL_SECONDS: int = 900

    # Phase 9: RAG knowledge base. all-MiniLM-L6-v2 downloads once (~90MB)
    # from Hugging Face on first use, then caches locally - needs internet
    # for that one-time download, nothing after.
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    KB_COLLECTION_NAME: str = "financial_knowledge_base"

    # Phase 10/11: AI investment insight generation via LangChain.
    # LLM_PROVIDER picks the backend:
    #   "groq"      - Groq's hosted API (very fast, free tier, needs GROQ_API_KEY)
    #   "anthropic" - Claude (needs ANTHROPIC_API_KEY)
    #   "ollama"    - fully local (needs Ollama installed and the model pulled)
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"
    OLLAMA_MODEL: str = "llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_TEMPERATURE: float = 0.1

    DEFAULT_HISTORY_PERIOD: str = "1y"
    DEFAULT_HISTORY_INTERVAL: str = "1d"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
