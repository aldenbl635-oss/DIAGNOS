"""
EmbeddingService — lightweight, singleton embedding engine.

Uses sentence-transformers all-MiniLM-L6-v2 (local, no API key).
Loads the model exactly once per process. All code paths share the same instance.
"""

import logging
from typing import List, Union
import numpy as np

logger = logging.getLogger(__name__)

_MODEL = None  # Singleton

def _get_model():
    global _MODEL
    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[EmbeddingService] Loading all-MiniLM-L6-v2 model...")
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[EmbeddingService] Model loaded successfully.")
        except ImportError:
            logger.warning(
                "[EmbeddingService] sentence-transformers not installed. "
                "Falling back to zero-vector stub. Run: pip install sentence-transformers numpy"
            )
            _MODEL = _StubModel()
    return _MODEL


class _StubModel:
    """Fallback stub — returns zero vectors when sentence-transformers is unavailable."""

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True):
        if isinstance(texts, str):
            return np.zeros(384, dtype=np.float32)
        return [np.zeros(384, dtype=np.float32) for _ in texts]


class EmbeddingService:
    """
    Public interface for generating text embeddings.
    All callers should import and use this class.

    Usage:
        emb = EmbeddingService()
        vec = emb.embed("Does bright light make it worse?")
        vecs = emb.embed_batch(["Question 1", "Question 2"])
        sim = emb.cosine_similarity(vec_a, vec_b)
    """

    def __init__(self):
        self._model = _get_model()

    def embed(self, text: str) -> np.ndarray:
        """Embed a single string. Returns a 384-dim float32 numpy array."""
        return self._model.encode(
            text, convert_to_numpy=True, normalize_embeddings=True
        )

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed a list of strings in one forward pass."""
        if not texts:
            return []
        results = self._model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True
        )
        # Ensure it's always a list of arrays
        if isinstance(results, np.ndarray) and results.ndim == 2:
            return [results[i] for i in range(results.shape[0])]
        return list(results)

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two normalised vectors (dot product)."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def rank_by_similarity(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
        threshold: float = 0.30,
    ) -> List[dict]:
        """
        Embed query + candidates, return top-k candidates above threshold.
        Returns list of {"text": str, "score": float}.
        """
        if not candidates:
            return []

        q_vec = self.embed(query)
        c_vecs = self.embed_batch(candidates)

        scored = []
        for text, vec in zip(candidates, c_vecs):
            score = self.cosine_similarity(q_vec, vec)
            if score >= threshold:
                scored.append({"text": text, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
