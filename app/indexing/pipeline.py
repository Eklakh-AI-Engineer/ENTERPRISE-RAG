from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.indexing.embeddings import EmbeddingProvider
from app.persistence.chunks import ChunkRepository
from app.persistence.entities import DocumentRecord


@dataclass(frozen=True, slots=True)
class IndexingResult:
    chunk_count: int
    embedding_model: str
    embedding_dimension: int


class DocumentIndexingPipeline:
    """Chunk -> embedding -> durable vector-ready persistence boundary."""

    def __init__(self, *, embeddings: EmbeddingProvider, chunks: ChunkRepository) -> None:
        self.embeddings = embeddings
        self.chunks = chunks

    def run(self, *, document: DocumentRecord, chunk_records: list[dict[str, Any]]) -> IndexingResult:
        texts = [chunk["text"] for chunk in chunk_records]
        vectors: np.ndarray = self.embeddings.encode(texts)
        if len(vectors) != len(chunk_records):
            raise ValueError("embedding count does not match chunk count")
        self.chunks.upsert_for_document(
            document=document,
            chunks=chunk_records,
            embeddings=vectors.tolist(),
            embedding_model=self.embeddings.model_name,
        )
        return IndexingResult(
            chunk_count=len(chunk_records),
            embedding_model=self.embeddings.model_name,
            embedding_dimension=self.embeddings.dimension,
        )
