"""
The Phase 10 pipeline: retrieves grounded context from the Phase 9
knowledge base across four categories (fundamentals, technical, news,
social), then prompts an LLM - Claude or Ollama, chosen via LLM_PROVIDER -
to produce a structured, evidence-based investment summary at low
temperature. The system prompt explicitly forbids using pretrained
knowledge about the company; the model is only allowed to reason over
what was actually retrieved, which is what keeps this "RAG" rather than
"the model's opinion with extra steps."

Two entry points:
- generate_insight(): the one-shot structured summary shown when the chat
  first opens. Rebuilds the symbol's KB for freshness.
- chat(): grounded multi-turn follow-up Q&A. Reuses the already-built KB
  (no rebuild) and re-injects the retrieved context into every turn so the
  model stays evidence-based no matter how the conversation wanders.
"""
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import kb_builder, vector_store

SYSTEM_PROMPT = (
    "You are a financial analyst assistant. Base your analysis ONLY on the "
    "retrieved context provided below - do not rely on prior knowledge about "
    "this company, and do not speculate beyond what the context supports. "
    "If a category has no supporting context, say so explicitly rather than "
    "guessing or filling the gap with general knowledge.\n\n"
    "Evaluate the stock across these dimensions, using only the retrieved context:\n"
    "1. Company fundamentals\n"
    "2. EMA 50 & EMA 200 technical trend\n"
    "3. Recent financial news\n"
    "4. Public market sentiment (Reddit/StockTwits)\n"
    "5. Overall market outlook - a synthesis of the four points above\n\n"
    "End with a concise, evidence-based investment summary (2-3 sentences). "
    "Do not give direct buy/sell orders - describe what the evidence shows."
)

USER_PROMPT_TEMPLATE = (
    "Ticker: {symbol}\n\n"
    "Retrieved context:\n"
    "--- Fundamentals ---\n{fundamentals_context}\n\n"
    "--- Technical (EMA 50 / EMA 200) ---\n{technical_context}\n\n"
    "--- Recent News ---\n{news_context}\n\n"
    "--- Public Sentiment ---\n{social_context}\n\n"
    "Using ONLY the context above, produce the structured analysis described in your instructions."
)

# For follow-up turns the user can ask anything, so we drop the rigid
# 5-section structure and just keep the grounding rules + the retrieved
# context. The context is concatenated (not templated) so arbitrary user
# text and news punctuation can't collide with prompt-template braces.
CHAT_SYSTEM_PROMPT_HEADER = (
    "You are a financial analyst assistant helping a user understand the stock {symbol}. "
    "Ground every claim about THIS specific stock in the retrieved context below; if the "
    "context doesn't cover what's asked, say so plainly rather than inventing company-specific "
    "numbers, news, or events. You may explain general investing concepts (what an EMA is, what "
    "a P/E ratio means, how sentiment is read) from common knowledge. Never give direct buy/sell "
    "orders - describe what the evidence shows and let the user decide. Keep answers concise and "
    "conversational.\n\nRetrieved context for {symbol}:\n"
)


class AIInsightError(Exception):
    """Raised when the LLM call itself fails - missing API key, provider
    unreachable, Ollama not running locally, unknown LLM_PROVIDER, etc.
    The router turns this into a clean 503 rather than a raw traceback."""


def _format_docs(docs: list[dict], empty_message: str) -> str:
    if not docs:
        return empty_message
    return "\n".join(f"- {d['text']}" for d in docs)


def _format_context_block(context: dict) -> str:
    """One human-readable block covering all four retrieved categories -
    used to ground the follow-up chat turns."""
    return (
        "--- Fundamentals ---\n"
        + _format_docs(context["fundamentals"], "No fundamentals data available.")
        + "\n\n--- Technical (EMA 50 / EMA 200) ---\n"
        + _format_docs(context["technical"], "No technical data available.")
        + "\n\n--- Recent News ---\n"
        + _format_docs(context["news"], "No recent news found.")
        + "\n\n--- Public Sentiment ---\n"
        + _format_docs(context["social"], "No social sentiment data found.")
    )


def _sources_from_context(context: dict) -> list[dict]:
    return [
        {"doc_type": doc["metadata"].get("doc_type"), "text": doc["text"]}
        for category_docs in context.values()
        for doc in category_docs
    ]


def _build_llm(provider: Optional[str] = None) -> BaseChatModel:
    provider = (provider or settings.LLM_PROVIDER).lower()

    try:
        if provider == "groq":
            from langchain_groq import ChatGroq

            if not settings.GROQ_API_KEY:
                raise AIInsightError("GROQ_API_KEY is not set in .env - get a free key at https://console.groq.com/keys")
            return ChatGroq(
                model=settings.GROQ_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                api_key=settings.GROQ_API_KEY,
            )

        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            kwargs = {"model": settings.ANTHROPIC_MODEL, "temperature": settings.LLM_TEMPERATURE}
            if settings.ANTHROPIC_API_KEY:
                kwargs["api_key"] = settings.ANTHROPIC_API_KEY
            return ChatAnthropic(**kwargs)

        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=settings.LLM_TEMPERATURE,
            )

        raise AIInsightError(f"Unknown LLM_PROVIDER '{provider}' - use 'groq', 'anthropic', or 'ollama'")
    except AIInsightError:
        raise
    except Exception as e:
        hint = {
            "groq": "Check GROQ_API_KEY is set in .env and the model name is valid.",
            "anthropic": "Check ANTHROPIC_API_KEY is set in .env.",
        }.get(
            provider,
            "Make sure Ollama is running (`ollama serve`) and the model is "
            f"pulled (`ollama pull {settings.OLLAMA_MODEL}`).",
        )
        raise AIInsightError(f"Could not initialize the '{provider}' LLM provider ({e}). " + hint) from e


def retrieve_context(
    symbol: str,
    db: Session,
    store: Optional[vector_store.VectorStore] = None,
    rebuild: bool = True,
) -> dict:
    """Pulls the most relevant documents per category. When `rebuild` is
    True (the default, used for the initial insight) it first re-indexes the
    symbol's KB for freshness - cheap, it's an upsert. Follow-up chat turns
    pass rebuild=False to reuse the already-built KB and skip the slow
    yfinance/news refetch."""
    symbol = symbol.upper()
    store = store or vector_store.get_vector_store()
    if rebuild:
        kb_builder.build_knowledge_base_for_symbol(symbol, db, store=store)

    return {
        "fundamentals": store.query(
            symbol, f"{symbol} fundamentals sector market cap valuation", top_k=2, doc_types=["fundamentals"]
        ),
        "technical": store.query(
            symbol, f"{symbol} EMA moving average trend price", top_k=2, doc_types=["technical"]
        ),
        "news": store.query(symbol, f"{symbol} recent news", top_k=5, doc_types=["news"]),
        "social": store.query(symbol, f"{symbol} sentiment discussion opinion", top_k=5, doc_types=["social"]),
    }


def generate_insight(
    symbol: str,
    db: Session,
    store: Optional[vector_store.VectorStore] = None,
    llm: Optional[BaseChatModel] = None,
) -> dict:
    symbol = symbol.upper()

    context = retrieve_context(symbol, db, store=store)  # VectorStoreError, if raised, propagates as-is

    chat_model = llm or _build_llm()
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", USER_PROMPT_TEMPLATE)])
    chain = prompt | chat_model

    try:
        response = chain.invoke(
            {
                "symbol": symbol,
                "fundamentals_context": _format_docs(context["fundamentals"], "No fundamentals data available."),
                "technical_context": _format_docs(context["technical"], "No technical data available."),
                "news_context": _format_docs(context["news"], "No recent news found."),
                "social_context": _format_docs(context["social"], "No social sentiment data found."),
            }
        )
    except AIInsightError:
        raise
    except Exception as e:
        raise AIInsightError(f"The LLM call failed: {e}") from e

    return {"symbol": symbol, "insight": response.content, "sources": _sources_from_context(context)}


def chat(
    symbol: str,
    db: Session,
    messages: list[dict],
    store: Optional[vector_store.VectorStore] = None,
    llm: Optional[BaseChatModel] = None,
) -> dict:
    """Grounded follow-up Q&A. `messages` is the running conversation as a
    list of {"role": "user"|"assistant", "content": str}. We re-query (but
    do NOT rebuild) the KB, prepend the retrieved context as a system
    message, replay the conversation, and return the model's next reply."""
    symbol = symbol.upper()

    context = retrieve_context(symbol, db, store=store, rebuild=False)
    context_block = _format_context_block(context)

    chat_model = llm or _build_llm()

    # Built by concatenation, not a prompt template, so braces/newlines in
    # the retrieved docs or the user's own questions can never break it.
    system_content = CHAT_SYSTEM_PROMPT_HEADER.format(symbol=symbol) + context_block

    lc_messages: list = [SystemMessage(content=system_content)]
    for m in messages:
        content = m.get("content", "")
        if m.get("role") == "assistant":
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))

    try:
        response = chat_model.invoke(lc_messages)
    except AIInsightError:
        raise
    except Exception as e:
        raise AIInsightError(f"The LLM call failed: {e}") from e

    return {"symbol": symbol, "reply": response.content, "sources": _sources_from_context(context)}
