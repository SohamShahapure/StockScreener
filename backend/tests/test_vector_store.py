"""
Uses chromadb's EphemeralClient (in-memory, no disk, no network) plus the
FakeEmbeddingFunction from fakes.py, so these tests run instantly and prove
the upsert/query/delete mechanics work correctly - independent of the real
sentence-transformers model, which needs a one-time download this sandbox
can't reach.
"""
import chromadb
import pytest

from app.services.vector_store import VectorStore, VectorStoreError
from tests.fakes import FakeEmbeddingFunction


@pytest.fixture()
def store(request):
    client = chromadb.EphemeralClient()
    # Unique per-test collection name - guards against any shared state
    # across EphemeralClient instances within the same test process.
    collection_name = f"test_kb_{request.node.name}"
    return VectorStore(client=client, embedding_function=FakeEmbeddingFunction(), collection_name=collection_name)


def test_upsert_and_count(store):
    docs = [
        {"id": "a:1", "text": "Apple reported strong iPhone sales", "metadata": {"symbol": "AAPL", "doc_type": "news"}},
        {"id": "a:2", "text": "Apple stock rises on earnings beat", "metadata": {"symbol": "AAPL", "doc_type": "news"}},
    ]
    store.upsert_documents(docs)
    assert store.count() == 2


def test_upsert_is_idempotent_on_id(store):
    doc = {"id": "a:1", "text": "Apple reported strong iPhone sales", "metadata": {"symbol": "AAPL", "doc_type": "news"}}
    store.upsert_documents([doc])
    store.upsert_documents([doc])  # same id again
    assert store.count() == 1


def test_query_filters_by_symbol(store):
    store.upsert_documents(
        [
            {"id": "a:1", "text": "Apple earnings beat expectations", "metadata": {"symbol": "AAPL", "doc_type": "news"}},
            {"id": "t:1", "text": "Tesla recalls vehicles over software bug", "metadata": {"symbol": "TSLA", "doc_type": "news"}},
        ]
    )

    results = store.query("AAPL", "earnings", top_k=5)
    assert len(results) == 1
    assert results[0]["metadata"]["symbol"] == "AAPL"


def test_query_filters_by_doc_type(store):
    store.upsert_documents(
        [
            {"id": "a:fund", "text": "Apple market cap and P/E ratio details", "metadata": {"symbol": "AAPL", "doc_type": "fundamentals"}},
            {"id": "a:news", "text": "Apple earnings beat expectations this quarter", "metadata": {"symbol": "AAPL", "doc_type": "news"}},
        ]
    )

    results = store.query("AAPL", "Apple", top_k=5, doc_types=["fundamentals"])
    assert len(results) == 1
    assert results[0]["metadata"]["doc_type"] == "fundamentals"


def test_query_returns_empty_list_for_unknown_symbol(store):
    store.upsert_documents(
        [{"id": "a:1", "text": "Apple earnings beat expectations", "metadata": {"symbol": "AAPL", "doc_type": "news"}}]
    )
    assert store.query("ZZZZ", "earnings") == []


def test_delete_symbol_removes_only_that_symbols_docs(store):
    store.upsert_documents(
        [
            {"id": "a:1", "text": "Apple earnings news", "metadata": {"symbol": "AAPL", "doc_type": "news"}},
            {"id": "t:1", "text": "Tesla recall news", "metadata": {"symbol": "TSLA", "doc_type": "news"}},
        ]
    )
    store.delete_symbol("AAPL")
    assert store.count() == 1
    remaining = store.query("TSLA", "recall")
    assert len(remaining) == 1


def test_upsert_empty_list_is_a_safe_noop(store):
    store.upsert_documents([])
    assert store.count() == 0


def test_construction_failure_raises_clean_vectorstoreerror(monkeypatch):
    """Reproduces the exact real-world failure: the embedding model can't
    be loaded (e.g. no internet for the one-time Hugging Face download).
    Must surface as a clear VectorStoreError, not a raw exception."""
    from chromadb.utils import embedding_functions

    def broken_factory(*args, **kwargs):
        raise OSError("We couldn't connect to 'https://huggingface.co' to load the files")

    monkeypatch.setattr(embedding_functions, "SentenceTransformerEmbeddingFunction", broken_factory)

    with pytest.raises(VectorStoreError, match="Could not initialize the knowledge base"):
        VectorStore(client=chromadb.EphemeralClient())  # no embedding_function passed - uses the broken factory


def test_get_vector_store_does_not_cache_a_failed_construction(monkeypatch):
    """If construction fails once, the module-level singleton must stay
    unset so a later call (e.g. once internet is back) can succeed instead
    of being stuck on a permanently broken cached instance."""
    from app.services import vector_store as vs_module

    vs_module._store = None  # ensure clean slate regardless of test order

    call_count = {"n": 0}

    class SometimesBrokenVectorStore:
        def __init__(self):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise VectorStoreError("simulated first-attempt failure")

    monkeypatch.setattr(vs_module, "VectorStore", SometimesBrokenVectorStore)

    with pytest.raises(VectorStoreError):
        vs_module.get_vector_store()
    assert vs_module._store is None  # not cached after failure

    result = vs_module.get_vector_store()  # second attempt succeeds
    assert result is not None
    assert vs_module._store is result

    vs_module._store = None  # cleanup so other tests aren't affected
