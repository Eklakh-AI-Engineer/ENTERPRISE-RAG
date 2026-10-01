from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import uuid4

from app.persistence.entities import DocumentRecord, IngestionJobRecord, utcnow
from app.persistence.repositories import DocumentRepository, IngestionJobRepository


class DocumentValidationError(ValueError):
    """Raised when document input violates the application contract."""


@dataclass(frozen=True, slots=True)
class DocumentSubmission:
    document: DocumentRecord
    ingestion_job: IngestionJobRecord
    deduplicated: bool


class DocumentService:
    """Own document identity and upload-to-job lifecycle rules.

    Storage itself is deliberately outside this service. The service only creates
    the deterministic storage path that the eventual Supabase Storage adapter will
    materialize.
    """

    def __init__(
        self,
        documents: DocumentRepository,
        ingestion_jobs: IngestionJobRepository,
    ) -> None:
        self.documents = documents
        self.ingestion_jobs = ingestion_jobs

    def submit(
        self,
        *,
        organization_id: str,
        owner_user_id: str,
        filename: str,
        content: bytes,
        pipeline_version: str,
    ) -> DocumentSubmission:
        self._validate(
            organization_id=organization_id,
            owner_user_id=owner_user_id,
            filename=filename,
            content=content,
            pipeline_version=pipeline_version,
        )

        content_hash = hashlib.sha256(content).hexdigest()
        existing = self.documents.get_by_content(
            organization_id, content_hash, pipeline_version
        )
        if existing is not None:
            return self._existing_submission(
                existing,
                content_hash=content_hash,
                pipeline_version=pipeline_version,
            )

        document_id = str(uuid4())
        document = DocumentRecord(
            id=document_id,
            organization_id=organization_id,
            owner_user_id=owner_user_id,
            filename=filename,
            storage_path=(
                f"organizations/{organization_id}/documents/"
                f"{document_id}/{filename}"
            ),
            content_hash=content_hash,
            pipeline_version=pipeline_version,
        )
        self.documents.save(document)

        job = IngestionJobRecord(
            id=str(uuid4()),
            organization_id=organization_id,
            document_id=document.id,
            pipeline_version=pipeline_version,
            content_hash=content_hash,
        )
        self.ingestion_jobs.create(job)

        return DocumentSubmission(
            document=document,
            ingestion_job=job,
            deduplicated=False,
        )

    def _existing_submission(
        self,
        document: DocumentRecord,
        *,
        content_hash: str,
        pipeline_version: str,
    ) -> DocumentSubmission:
        # A duplicate upload is an idempotent submission. If the original job is
        # already represented by the production repository, the adapter can return
        # it here; the current repository boundary intentionally exposes jobs by ID.
        # For the in-memory phase, create a fresh PENDING job only when the existing
        # document is not already terminal/active. This keeps retry behavior explicit.
        job = IngestionJobRecord(
            id=str(uuid4()),
            organization_id=document.organization_id,
            document_id=document.id,
            pipeline_version=pipeline_version,
            content_hash=content_hash,
        )
        self.ingestion_jobs.create(job)
        return DocumentSubmission(
            document=document,
            ingestion_job=job,
            deduplicated=True,
        )

    @staticmethod
    def _validate(
        *,
        organization_id: str,
        owner_user_id: str,
        filename: str,
        content: bytes,
        pipeline_version: str,
    ) -> None:
        if not organization_id.strip():
            raise DocumentValidationError("organization_id is required.")
        if not owner_user_id.strip():
            raise DocumentValidationError("owner_user_id is required.")
        if not filename.strip():
            raise DocumentValidationError("filename is required.")
        if "/" in filename or "\\" in filename:
            raise DocumentValidationError("filename must not contain path separators.")
        if not content:
            raise DocumentValidationError("document content must not be empty.")
        if not pipeline_version.strip():
            raise DocumentValidationError("pipeline_version is required.")
