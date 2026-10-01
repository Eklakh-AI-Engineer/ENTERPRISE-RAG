from __future__ import annotations

from datetime import datetime
from typing import Any

from app.persistence.entities import DocumentRecord, IngestionJobRecord


class SupabasePersistenceError(RuntimeError):
    """Raised when the Supabase adapter cannot persist a domain record."""


def _data(response: Any) -> Any:
    if hasattr(response, "data"):
        return response.data
    return response


def _one(response: Any) -> dict[str, Any] | None:
    value = _data(response)
    if value is None:
        return None
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _require_one(response: Any) -> dict[str, Any]:
    row = _one(response)
    if row is None:
        raise SupabasePersistenceError("Expected a Supabase row but received none.")
    return row


def _error(response: Any) -> Any:
    return getattr(response, "error", None)


def _raise_on_error(response: Any) -> None:
    error = _error(response)
    if error:
        raise SupabasePersistenceError(str(error))


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class SupabaseDocumentRepository:
    """Supabase adapter for the DocumentRepository contract.

    The client is injected so the application can configure either a normal
    user-JWT client or a trusted worker client without coupling domain code to
    Supabase authentication details.
    """

    def __init__(self, client: Any) -> None:
        self.client = client

    def get(self, document_id: str, organization_id: str) -> DocumentRecord | None:
        response = (
            self.client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("organization_id", organization_id)
            .maybe_single()
            .execute()
        )
        _raise_on_error(response)
        row = _one(response)
        return _document(row) if row else None

    def get_by_content(
        self,
        organization_id: str,
        content_hash: str,
        pipeline_version: str,
    ) -> DocumentRecord | None:
        response = (
            self.client.table("documents")
            .select("*")
            .eq("organization_id", organization_id)
            .eq("content_hash", content_hash)
            .eq("pipeline_version", pipeline_version)
            .maybe_single()
            .execute()
        )
        _raise_on_error(response)
        row = _one(response)
        return _document(row) if row else None

    def save(self, document: DocumentRecord) -> DocumentRecord:
        response = (
            self.client.table("documents")
            .upsert(_document_payload(document), on_conflict="id")
            .select("*")
            .single()
            .execute()
        )
        _raise_on_error(response)
        return _document(_require_one(response))


class SupabaseIngestionJobRepository:
    """Supabase adapter for persisted ingestion jobs.

    Normal create/update operations use RLS-aware table calls. Worker claiming
    is intentionally exposed through the database RPC added to schema.sql so
    the claim is atomic rather than a read-then-write race.
    """

    def __init__(self, client: Any) -> None:
        self.client = client

    def get(self, job_id: str, organization_id: str) -> IngestionJobRecord | None:
        response = (
            self.client.table("ingestion_jobs")
            .select("*")
            .eq("id", job_id)
            .eq("organization_id", organization_id)
            .maybe_single()
            .execute()
        )
        _raise_on_error(response)
        row = _one(response)
        return _job(row) if row else None

    def get_by_document(
        self,
        document_id: str,
        organization_id: str,
    ) -> IngestionJobRecord | None:
        response = (
            self.client.table("ingestion_jobs")
            .select("*")
            .eq("document_id", document_id)
            .eq("organization_id", organization_id)
            .maybe_single()
            .execute()
        )
        _raise_on_error(response)
        row = _one(response)
        return _job(row) if row else None

    def create(self, job: IngestionJobRecord) -> IngestionJobRecord:
        response = (
            self.client.table("ingestion_jobs")
            .insert(_job_payload(job))
            .select("*")
            .single()
            .execute()
        )
        _raise_on_error(response)
        return _job(_require_one(response))

    def update(self, job: IngestionJobRecord) -> IngestionJobRecord:
        response = (
            self.client.table("ingestion_jobs")
            .update(_job_payload(job))
            .eq("id", job.id)
            .eq("organization_id", job.organization_id)
            .select("*")
            .single()
            .execute()
        )
        _raise_on_error(response)
        return _job(_require_one(response))

    def claim_atomic(
        self,
        *,
        organization_id: str,
        lease_seconds: int,
    ) -> IngestionJobRecord | None:
        response = self.client.rpc(
            "claim_ingestion_job",
            {
                "p_organization_id": organization_id,
                "p_lease_seconds": lease_seconds,
            },
        ).execute()
        _raise_on_error(response)
        row = _one(response)
        return _job(row) if row else None


def _document(row: dict[str, Any]) -> DocumentRecord:
    return DocumentRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        owner_user_id=row["owner_user_id"],
        filename=row["filename"],
        storage_path=row["storage_path"],
        content_hash=row["content_hash"],
        pipeline_version=row["pipeline_version"],
        status=row.get("status", "UPLOADED"),
        page_count=row.get("page_count"),
        metadata=row.get("metadata") or {},
        created_at=_parse_dt(row.get("created_at")) or DocumentRecord.__dataclass_fields__["created_at"].default_factory(),
        updated_at=_parse_dt(row.get("updated_at")) or DocumentRecord.__dataclass_fields__["updated_at"].default_factory(),
    )


def _job(row: dict[str, Any]) -> IngestionJobRecord:
    return IngestionJobRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        document_id=row["document_id"],
        status=row.get("status", "PENDING"),
        pipeline_version=row["pipeline_version"],
        content_hash=row["content_hash"],
        attempt_count=row.get("attempt_count", 0),
        lease_until=_parse_dt(row.get("lease_until")),
        last_error=row.get("last_error"),
        created_at=_parse_dt(row.get("created_at")) or IngestionJobRecord.__dataclass_fields__["created_at"].default_factory(),
        updated_at=_parse_dt(row.get("updated_at")) or IngestionJobRecord.__dataclass_fields__["updated_at"].default_factory(),
    )


def _document_payload(document: DocumentRecord) -> dict[str, Any]:
    return {
        "id": document.id,
        "organization_id": document.organization_id,
        "owner_user_id": document.owner_user_id,
        "filename": document.filename,
        "storage_path": document.storage_path,
        "content_hash": document.content_hash,
        "pipeline_version": document.pipeline_version,
        "status": document.status,
        "page_count": document.page_count,
        "metadata": document.metadata,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }


def _job_payload(job: IngestionJobRecord) -> dict[str, Any]:
    return {
        "id": job.id,
        "organization_id": job.organization_id,
        "document_id": job.document_id,
        "status": job.status,
        "pipeline_version": job.pipeline_version,
        "content_hash": job.content_hash,
        "attempt_count": job.attempt_count,
        "lease_until": job.lease_until.isoformat() if job.lease_until else None,
        "last_error": job.last_error,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }
