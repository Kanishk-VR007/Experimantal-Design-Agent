"""
Embedder — Stub
===============
Provides a get_embedder() factory used at startup to warm up the embedding model.
Replace the body with a real sentence-transformers or OpenAI embeddings call.
"""


class _StubEmbedder:
    """No-op embedder. Replace with a real implementation."""

    def embed(self, text: str) -> list:
        # Return a zeroed 384-dim vector as a placeholder
        return [0.0] * 384

    def embed_batch(self, texts: list) -> list:
        return [self.embed(t) for t in texts]


_instance = None


def get_embedder() -> _StubEmbedder:
    """Return a singleton embedder instance (lazy init)."""
    global _instance
    if _instance is None:
        _instance = _StubEmbedder()
        print("[Embedder] Using stub embedder — replace core/embedder.py for real embeddings")
    return _instance
