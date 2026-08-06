"""
App entrypoint. Run with:  uvicorn app.main:app --reload
Docs available at:         http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings
from app.db.database import init_db
from app.routers import ai_insight, auth, knowledge_base, news, social, stocks, watchlist


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# ORJSONResponse (Phase 11): faster JSON serialization than the stdlib
# encoder, and it renders non-finite floats (NaN/Inf) as null instead of
# crashing - defense-in-depth on top of the schema-level sanitizing.
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for the AI Stock Screener - Phases 1-11: stock data, persistence, news, social sentiment, NLP, a RAG knowledge base, LLM investment insights, and per-user accounts.",
    version="0.11.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(watchlist.router)
app.include_router(news.router)
app.include_router(social.router)
app.include_router(knowledge_base.router)
app.include_router(ai_insight.router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}
