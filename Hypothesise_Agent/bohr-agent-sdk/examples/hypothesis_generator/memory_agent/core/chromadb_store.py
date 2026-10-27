"""
ChromaDB Store — Stub
=====================
Placeholder for a vector-store integration.
Swap this implementation out to connect a real ChromaDB or Pinecone instance.

The ImprovementEngine calls _get_collection() only during non-dry-run pruning.
"""

from typing import Any

# Map memory type names → collection names
COLLECTIONS: dict = {
    "chat_history"          : "chat_history",
    "experiment_result"     : "experiment_results",
    "hypothesis_procedure"  : "hypothesis_procedures",
    "agent_conversation"    : "agent_conversations",
    "model_learning"        : "model_learnings",
}


class _MockCollection:
    """Minimal stand-in that logs operations instead of executing them."""

    def __init__(self, name: str):
        self.name = name

    def delete(self, ids: list):
        print(f"[chromadb_store] (stub) Would delete {ids} from '{self.name}'")

    def query(self, query_embeddings=None, n_results: int = 5, **kwargs):
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    def add(self, **kwargs):
        print(f"[chromadb_store] (stub) add() called on '{self.name}' — not persisted")

    def get(self, **kwargs):
        return {"ids": [], "documents": [], "metadatas": []}


def _get_collection(name: str) -> _MockCollection:
    """
    Return a collection object for the given name.
    Replace this with a real ChromaDB client call:

        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        return client.get_or_create_collection(name)
    """
    return _MockCollection(name)


def cloud_available() -> bool:
    """Returns True if a cloud vector store (Pinecone etc.) is reachable."""
    return False
