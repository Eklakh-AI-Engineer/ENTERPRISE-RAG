from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.ingestion.pipeline import PdfIngestionPipeline
from app.persistence.entities import DocumentRecord, IngestionJobRecord
from app.persistence.repositories import DocumentRepository, WorkerJobRepository
from app.indexing.pipeline import DocumentIndexingPipeline
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
        jobs: WorkerJobRepository,
        documents: DocumentRepository,
        storage: DocumentStorage,
        pipeline: PdfIngestionPipeline,
        indexer: DocumentIndexingPipeline,
        config: WorkerConfig | None = None,
    ) -> None:
        self.jobs = jobs
        self.documents = documents
        self.storage = storage
        self.pipeline = pipeline
        self.indexer = indexer
        self.config = config or WorkerConfig()
        self.lifecycle = IngestionService(jobs)

    def run_once(self, *, organization_id: str) -> IngestionJobRecord | None:
        """Atomically claim the oldest eligible job and process it."""
        job = self.jobs.claim_atomic(
            organization_id=organization_id,
            lease_seconds=self.config.lease_seconds,
        )
        if job is None:
            return None
        return self.process_claimed(job)

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
            document.status = "PROCESSING"
            self.documents.save(document)
            content = self.storage.download(path=document.storage_path)
            artifact = self.pipeline.run(
                content=content,
                filename=document.filename,
                document_id=document.id,
            )
            document.page_count = len(artifact.pages)
            document.status = "INDEXING"
            self.documents.save(document)
            self.indexer.run(document=document, chunk_records=artifact.chunks)
            document.status = "READY"
            self.documents.save(document)
            return self.lifecycle.complete(
                job_id=job.id,
                organization_id=job.organization_id,
            )
        except Exception as exc:
            document.status = "FAILED"
            try:
                self.documents.save(document)
            except Exception:
                pass
            return self.lifecycle.fail(
                job_id=job.id,
                organization_id=job.organization_id,
                error=f"{type(exc).__name__}: {exc}",
            )
