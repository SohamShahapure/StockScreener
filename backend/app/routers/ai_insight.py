"""
The one endpoint Phase 10 adds: generates a grounded, evidence-based
investment summary for a symbol by retrieving context from the Phase 9
knowledge base and prompting an LLM (Claude or Ollama) via LangChain.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.schemas import AIChatRequest, AIChatResponse, AIInsightResponse
from app.services import ai_insight, vector_store

router = APIRouter(prefix="/api/ai-insight", tags=["ai_insight"])


@router.post("/{symbol}", response_model=AIInsightResponse)
def generate_insight(symbol: str, db: Session = Depends(get_db)):
    """Rebuilds the symbol's knowledge base, retrieves grounded context
    across fundamentals/technical/news/social, and asks the configured LLM
    provider for a structured investment summary. Returns 503 (not a crash)
    if the vector store or LLM provider can't be reached - both surface a
    specific, actionable message."""
    try:
        result = ai_insight.generate_insight(symbol, db)
    except (vector_store.VectorStoreError, ai_insight.AIInsightError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    return AIInsightResponse(symbol=result["symbol"], provider=settings.LLM_PROVIDER, insight=result["insight"], sources=result["sources"])


@router.post("/{symbol}/chat", response_model=AIChatResponse)
def chat(symbol: str, req: AIChatRequest, db: Session = Depends(get_db)):
    """Follow-up Q&A after the initial insight. Takes the running
    conversation (the initial insight included, as an assistant turn),
    re-grounds it in the symbol's already-built knowledge base, and returns
    the assistant's next reply. Same 503-on-unreachable contract as above."""
    if not req.messages:
        raise HTTPException(status_code=422, detail="messages must not be empty")
    try:
        result = ai_insight.chat(symbol, db, [m.model_dump() for m in req.messages])
    except (vector_store.VectorStoreError, ai_insight.AIInsightError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    return AIChatResponse(symbol=result["symbol"], provider=settings.LLM_PROVIDER, reply=result["reply"], sources=result["sources"])
