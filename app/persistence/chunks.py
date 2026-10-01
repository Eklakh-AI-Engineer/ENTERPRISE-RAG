from __future__ import annotations

from typing import Any, Protocol

from app.persistence.entities import DocumentRecord


class ChunkRepository(Protocol):
    """Durable chunk/evidence persistence boundary."""

    def upsert_for_document(
        self,
        *,
        document: DocumentRecord,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        embedding_model: str,
    ) -> int: ...
