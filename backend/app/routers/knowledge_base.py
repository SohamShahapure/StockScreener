"""
Two endpoints: build (or rebuild) a symbol's knowledge base from whatever
fundamentals/technicals/news/social data currently exists, and query it.
Phase 10's LLM pipeline will call the underlying services directly rather
than going through HTTP, but these endpoints exist so the KB is inspectable
and testable on its own - important for a RAG system, since "is retrieval
actually returning relevant context" needs to be checkable independently of
whether the LLM step is working.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.schemas import KnowledgeBaseBuildResponse, KnowledgeBaseQueryResult
from app.services import kb_builder, vector_store

router = APIRouter(prefix="/api/kb", tags=["knowledge_base"])


@router.post("/{symbol}/build", response_model=KnowledgeBaseBuildResponse)
def build_kb(symbol: str, db: Session = Depends(get_db)):
    """Builds/refreshes the knowledge base for a symbol. Safe to call
    repeatedly - upsert means re-indexing overwrites rather than duplicates."""
    try:
        return kb_builder.build_knowledge_base_for_symbol(symbol, db)
    except vector_store.VectorStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/{symbol}/query", response_model=list[KnowledgeBaseQueryResult])
def query_kb(
    symbol: str,
    q: str = Query(..., min_length=1, description="Natural-language query, e.g. 'is sentiment bullish?'"),
    top_k: int = Query(5, ge=1, le=20),
):
    """Retrieves the most relevant indexed documents for a symbol. Build
    the KB first via POST /{symbol}/build, or this will just return an
    empty list."""
    try:
        store = vector_store.get_vector_store()
        raw_results = store.query(symbol, q, top_k=top_k)
    except vector_store.VectorStoreError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return [KnowledgeBaseQueryResult.from_raw(r) for r in raw_results]
