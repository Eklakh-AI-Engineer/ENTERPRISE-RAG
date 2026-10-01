from __future__ import annotations

from typing import Protocol

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingProvider(Protocol):
    model_name: str
    dimension: int

    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbeddingProvider:
    """Normalized embedding provider matching the existing FAISS baseline."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimension = int(self.model.get_sentence_embedding_dimension())

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype="float32")
        vectors = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError("Embedding provider returned an unexpected shape.")
        return vectors
