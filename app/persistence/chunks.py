from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.persistence.entities import DocumentRecord


@dataclass(frozen=True, slots=True)
class ChunkSearchResult:
    id: str
    document_id: str
    chunk_id: str
    content: str
    page: int
    section: str | None
    start_char: int | None
    end_char: int | None
    similarity: float


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

    def search_similar(
        self,
        *,
        organization_id: str,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[ChunkSearchResult]: ...
