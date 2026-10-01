from __future__ import annotations

from typing import Protocol

from app.persistence.entities import DocumentRecord, IngestionJobRecord


class AtomicJobClaimer(Protocol):
    """Production worker contract backed by a database transaction/RPC."""

    def claim_atomic(
        self, *, organization_id: str, lease_seconds: int
    ) -> IngestionJobRecord | None: ...


class ChunkRepository(Protocol):
    """Database boundary for durable chunk/evidence persistence."""

    def replace_for_document(
        self, *, document: DocumentRecord, chunks: list[dict]
    ) -> int: ...


class VectorIndexRepository(Protocol):
    """Dense-index boundary; implementation may be pgvector or a local adapter."""

    def upsert_document_chunks(self, *, document_id: str, chunks: list[dict]) -> int: ...


class LexicalIndexRepository(Protocol):
    """Tenant-scoped BM25 lifecycle boundary."""

    def rebuild_organization(self, *, organization_id: str) -> None: ...

    def delete_document(self, *, organization_id: str, document_id: str) -> None: ...
