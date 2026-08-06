"""
The Phase 9 orchestrator: pulls a symbol's fundamentals+technicals (Phase 2),
news (Phase 5), and social posts (Phase 7), each already cleaned and
sentiment-tagged by Phase 8, turns them into documents (kb_documents.py),
and upserts them into the vector store (vector_store.py). This is the one
function Phase 10's RAG pipeline will call before querying for context.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.db import crud
from app.services import kb_documents, stock_service, vector_store
from app.services.data_fetch import TickerNotFoundError, UpstreamDataError


def build_knowledge_base_for_symbol(
    symbol: str, db: Session, store: Optional[vector_store.VectorStore] = None
) -> dict:
    symbol = symbol.upper()
    store = store or vector_store.get_vector_store()
    documents: list[dict] = []

    # Fundamentals + technicals: best-effort. If yfinance is unreachable or
    # the ticker is invalid, the KB still builds from whatever news/social
    # data exists rather than failing outright.
    try:
        summary = stock_service.get_stock_summary(symbol, db)
        documents.append(kb_documents.build_fundamentals_document(symbol, summary.company))
        documents.append(kb_documents.build_technical_document(symbol, summary.indicators))
    except (TickerNotFoundError, UpstreamDataError):
        pass

    for article in crud.get_latest_news(db, symbol, limit=10):
        documents.append(kb_documents.build_news_document(article))

    for source in ("reddit", "stocktwits"):
        for post in crud.get_latest_social(db, symbol, source, limit=10):
            documents.append(kb_documents.build_social_document(post))

    store.upsert_documents(documents)

    return {"symbol": symbol, "documents_indexed": len(documents)}
