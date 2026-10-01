from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.ingestion.pipeline import PdfIngestionPipeline
from app.persistence.entities import DocumentRecord, IngestionJobRecord
from app.persistence.repositories import DocumentRepository, IngestionJobRepository
from app.services.ingestion import IngestionService
from app.storage.base import DocumentStorage


class ChunkSink(Protocol):
    """Persistence/indexing boundary for pipeline chunks."""

    def persist(self, *, document: DocumentRecord, chunks: list[dict]) -> None: ...


@dataclass(frozen=True, slots=True)
class WorkerConfig:
    lease_seconds: int = 300


class IngestionWorker:
    """One-job-at-a-time worker orchestration.

    Atomic job claiming belongs to the production repository adapter. This class
    only coordinates the claimed job and never performs a read-then-write claim.
    """

    def __init__(
        self,
        *,
        jobs: IngestionJobRepository,
        documents: DocumentRepository,
        storage: DocumentStorage,
        pipeline: PdfIngestionPipeline,
        chunks: ChunkSink,
        config: WorkerConfig | None = None,
    ) -> None:
        self.jobs = jobs
        self.documents = documents
        self.storage = storage
        self.pipeline = pipeline
        self.chunks = chunks
        self.config = config or WorkerConfig()
        self.lifecycle = IngestionService(jobs)

    def process_claimed(self, job: IngestionJobRecord) -> IngestionJobRecord:
        if job.status != IngestionService.ACTIVE:
            raise ValueError("worker requires a PROCESSING job claimed by the worker")
        document = self.documents.get(job.document_id, job.organization_id)
        if document is None:
            return self.lifecycle.fail(
                job_id=job.id,
                organization_id=job.organization_id,
                error="Document record not found for ingestion job.",
            )

        try:
            content = self.storage.download(path=document.storage_path)
            artifact = self.pipeline.run(
                content=content,
                filename=document.filename,
                document_id=document.id,
            )
            self.chunks.persist(document=document, chunks=artifact.chunks)
            return self.lifecycle.complete(
                job_id=job.id,
                organization_id=job.organization_id,
            )
        except Exception as exc:
            return self.lifecycle.fail(
                job_id=job.id,
                organization_id=job.organization_id,
                error=f"{type(exc).__name__}: {exc}",
            )
