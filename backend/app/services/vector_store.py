"""
Wraps ChromaDB for the RAG knowledge base. Client and embedding function
are injectable (constructor args) rather than hardcoded module globals -
production code gets the real persistent client + sentence-transformers
model; tests inject an ephemeral in-memory client + a fake embedding
function, so the storage/retrieval *mechanics* are fully testable without
downloading a ~90MB model or touching a real disk-backed index.
"""
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import settings


class VectorStoreError(Exception):
    """Raised when the vector store can't be initialized or used. Most
    commonly this means the embedding model needs to download from Hugging
    Face on first use and there's no internet connection right now - the
    message is written to make that specific case obvious rather than
    surfacing a raw stack trace."""


class VectorStore:
    def __init__(self, client=None, embedding_function=None, collection_name: Optional[str] = None):
        try:
            self._client = client or chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            self._embedding_function = embedding_function or embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL_NAME
            )
            self._collection = self._client.get_or_create_collection(
                name=collection_name or settings.KB_COLLECTION_NAME,
                embedding_function=self._embedding_function,
            )
        except Exception as e:
            raise VectorStoreError(
                f"Could not initialize the knowledge base ({e}). If this is the first "
                f"time running this, the embedding model ('{settings.EMBEDDING_MODEL_NAME}') "
                f"needs to download from Hugging Face (~90MB, one-time only) - check your "
                f"internet connection and try again."
            ) from e

    def upsert_documents(self, documents: list[dict]) -> None:
        """Each doc: {"id": str, "text": str, "metadata": dict}. Upsert
        means re-indexing the same symbol is safe - existing docs with the
        same id are overwritten, not duplicated."""
        if not documents:
            return
        try:
            self._collection.upsert(
                ids=[d["id"] for d in documents],
                documents=[d["text"] for d in documents],
                metadatas=[d["metadata"] for d in documents],
            )
        except Exception as e:
            raise VectorStoreError(f"Failed to index documents in the knowledge base: {e}") from e

    def query(
        self,
        symbol: str,
        query_text: str,
        top_k: int = 5,
        doc_types: Optional[list[str]] = None,
    ) -> list[dict]:
        where: dict = {"symbol": symbol.upper()}
        if doc_types:
            where = {"$and": [{"symbol": symbol.upper()}, {"doc_type": {"$in": doc_types}}]}

        try:
            results = self._collection.query(query_texts=[query_text], n_results=top_k, where=where)
        except Exception as e:
            raise VectorStoreError(f"Failed to query the knowledge base: {e}") from e

        documents = results.get("documents") or [[]]
        metadatas = results.get("metadatas") or [[]]
        distances = results.get("distances") or [[]]

        return [
            {"text": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(documents[0], metadatas[0], distances[0])
        ]

    def delete_symbol(self, symbol: str) -> None:
        """Wipes every document for a symbol - used before a full rebuild
        so stale documents (e.g. a news article that's since been deleted
        upstream) don't linger forever."""
        try:
            self._collection.delete(where={"symbol": symbol.upper()})
        except Exception as e:
            raise VectorStoreError(f"Failed to delete documents for '{symbol}': {e}") from e

    def count(self) -> int:
        return self._collection.count()


_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Lazily-constructed singleton for the real app (routers/services) -
    the model only loads on first actual use, not at import time. If
    construction fails (e.g. no internet for the one-time model download),
    `_store` is never set, so the next call retries cleanly rather than
    permanently caching a broken instance."""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
