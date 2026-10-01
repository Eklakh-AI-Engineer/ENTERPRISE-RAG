from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import uuid4

from app.persistence.entities import DocumentRecord, IngestionJobRecord
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
            job = self.ingestion_jobs.get_by_document(
                existing.id, organization_id
            )
            if job is None:
                raise RuntimeError(
                    "Document exists without its ingestion job; "
                    "repository state is inconsistent."
                )
            return DocumentSubmission(
                document=existing,
                ingestion_job=job,
                deduplicated=True,
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
