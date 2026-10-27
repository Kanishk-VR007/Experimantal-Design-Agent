"""
Shared ChromaDB memory — imported by ALL agent wrappers.
One embedding model and one persist directory shared across the full pipeline.
All initialization is lazy to avoid model downloads at import time.
"""

from __future__ import annotations
from typing import Optional

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_classic.memory import VectorStoreRetrieverMemory

# One ChromaDB persist directory for the full pipeline
CHROMA_DIR = "./chroma_pipeline_db"

# Lazy singletons — created only on first use
_embeddings: Optional[HuggingFaceEmbeddings] = None
_collections: dict = {}


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Returns the shared embedding model, initializing it on first call."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embeddings


def get_collection(name: str) -> Chroma:
    """Returns (or creates) a named ChromaDB collection."""
    if name not in _collections:
        _collections[name] = Chroma(
            collection_name    = name,
            embedding_function = _get_embeddings(),
            persist_directory  = CHROMA_DIR,
        )
    return _collections[name]


def get_memory(collection_name: str, k: int = 4) -> VectorStoreRetrieverMemory:
    """Returns a LangChain memory object backed by ChromaDB."""
    db = get_collection(collection_name)
    return VectorStoreRetrieverMemory(
        retriever   = db.as_retriever(search_kwargs={"k": k}),
        memory_key  = "history",
        return_docs = True,
    )


class _LazyCollections:
    """Dict-like proxy that lazily creates ChromaDB collections on first access."""
    def __getitem__(self, name: str) -> Chroma:
        return get_collection(name)


# Drop-in replacement for the old COLLECTIONS dict — zero initialization at import time
COLLECTIONS = _LazyCollections()
