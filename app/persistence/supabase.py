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
        # A PostgreSQL function returning a composite row can be represented
        # by PostgREST as an object whose fields are all null when the
        # function returns NULL. Treat that as "no eligible job" rather than
        # attempting to re-read a null UUID.
        if not row or row.get("id") is None:
            return None

        claimed = _job(row)

        # The RPC atomically changes the row to PROCESSING. Re-read the row
        # when the RPC response does not expose the updated composite value
        # (for example, a stale/partial PostgREST representation). The worker
        # must never process a job using an unverified lifecycle state.
        if claimed.status != "PROCESSING":
            refreshed = self.get(claimed.id, organization_id)
            if refreshed is None:
                raise SupabasePersistenceError(
                    "Atomic claim returned a job that could not be re-read."
                )
            claimed = refreshed

        if claimed.status != "PROCESSING":
            raise SupabasePersistenceError(
                f"Atomic claim returned job {claimed.id} in unexpected state "
                f"{claimed.status!r}."
            )

        return claimed


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


from app.persistence.entities import AnswerRecord, CitationRecord, ConversationRecord, MessageRecord, RetrievalRunRecord


class SupabaseConversationRepository:
    """RLS-aware persistence adapter for authenticated conversations."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def get(self, conversation_id: str, user_id: str) -> ConversationRecord | None:
        response = (
            self.client.table("conversations")
            .select("*")
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        _raise_on_error(response)
        row = _one(response)
        return _conversation(row) if row else None

    def save(self, conversation: ConversationRecord) -> ConversationRecord:
        response = (
            self.client.table("conversations")
            .upsert(_conversation_payload(conversation), on_conflict="id")
            .select("*")
            .single()
            .execute()
        )
        _raise_on_error(response)
        return _conversation(_require_one(response))

    def add_message(self, message: MessageRecord) -> MessageRecord:
        response = (
            self.client.table("messages")
            .insert(_message_payload(message))
            .select("*")
            .single()
            .execute()
        )
        _raise_on_error(response)
        return _message(_require_one(response))


class SupabaseAnswerRepository:
    """RLS-aware persistence adapter for answers, citations, and telemetry."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def save_answer(self, answer: AnswerRecord) -> AnswerRecord:
        response = (
            self.client.table("answers")
            .insert(_answer_payload(answer))
            .select("*")
            .single()
            .execute()
        )
        _raise_on_error(response)
        return _answer(_require_one(response))

    def save_citation(self, citation: CitationRecord) -> CitationRecord:
        response = (
            self.client.table("citations")
            .insert(_citation_payload(citation))
            .select("*")
            .single()
            .execute()
        )
        _raise_on_error(response)
        return _citation(_require_one(response))

    def save_retrieval_run(self, run: RetrievalRunRecord) -> RetrievalRunRecord:
        response = (
            self.client.table("retrieval_runs")
            .insert(_retrieval_run_payload(run))
            .select("*")
            .single()
            .execute()
        )
        _raise_on_error(response)
        return _retrieval_run(_require_one(response))


def _conversation(row: dict[str, Any]) -> ConversationRecord:
    return ConversationRecord(
        id=row["id"], organization_id=row["organization_id"], user_id=row["user_id"],
        title=row.get("title"),
        created_at=_parse_dt(row.get("created_at")) or ConversationRecord.__dataclass_fields__["created_at"].default_factory(),
        updated_at=_parse_dt(row.get("updated_at")) or ConversationRecord.__dataclass_fields__["updated_at"].default_factory(),
    )


def _message(row: dict[str, Any]) -> MessageRecord:
    return MessageRecord(
        id=row["id"], conversation_id=row["conversation_id"], user_id=row["user_id"],
        role=row["role"], content=row["content"],
        created_at=_parse_dt(row.get("created_at")) or MessageRecord.__dataclass_fields__["created_at"].default_factory(),
    )


def _answer(row: dict[str, Any]) -> AnswerRecord:
    return AnswerRecord(
        id=row["id"], message_id=row["message_id"], query_text=row["query_text"],
        answer_text=row["answer_text"], retrieval_mode=row["retrieval_mode"],
        rewritten_query=row.get("rewritten_query"), faithfulness_status=row.get("faithfulness_status"),
        created_at=_parse_dt(row.get("created_at")) or AnswerRecord.__dataclass_fields__["created_at"].default_factory(),
    )


def _citation(row: dict[str, Any]) -> CitationRecord:
    return CitationRecord(
        id=row["id"], answer_id=row["answer_id"], document_chunk_id=row["document_chunk_id"],
        citation_label=row["citation_label"], valid=row.get("valid", False),
        created_at=_parse_dt(row.get("created_at")) or CitationRecord.__dataclass_fields__["created_at"].default_factory(),
    )


def _retrieval_run(row: dict[str, Any]) -> RetrievalRunRecord:
    return RetrievalRunRecord(
        id=row["id"], answer_id=row["answer_id"], organization_id=row["organization_id"],
        query_text=row["query_text"], retrieval_mode=row["retrieval_mode"],
        dense_count=row.get("dense_count", 0), bm25_count=row.get("bm25_count", 0),
        fused_count=row.get("fused_count", 0), reranked_count=row.get("reranked_count", 0),
        retrieval_latency_ms=row.get("retrieval_latency_ms"), rerank_latency_ms=row.get("rerank_latency_ms"),
        generation_latency_ms=row.get("generation_latency_ms"), verification_latency_ms=row.get("verification_latency_ms"),
        total_latency_ms=row.get("total_latency_ms"), input_tokens=row.get("input_tokens"),
        output_tokens=row.get("output_tokens"), estimated_cost=row.get("estimated_cost"),
        created_at=_parse_dt(row.get("created_at")) or RetrievalRunRecord.__dataclass_fields__["created_at"].default_factory(),
    )


def _conversation_payload(item: ConversationRecord) -> dict[str, Any]:
    return {
        "id": item.id, "organization_id": item.organization_id, "user_id": item.user_id,
        "title": item.title, "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat(),
    }


def _message_payload(item: MessageRecord) -> dict[str, Any]:
    return {
        "id": item.id, "conversation_id": item.conversation_id, "user_id": item.user_id,
        "role": item.role, "content": item.content, "created_at": item.created_at.isoformat(),
    }


def _answer_payload(item: AnswerRecord) -> dict[str, Any]:
    return {
        "id": item.id, "message_id": item.message_id, "query_text": item.query_text,
        "answer_text": item.answer_text, "retrieval_mode": item.retrieval_mode,
        "rewritten_query": item.rewritten_query, "faithfulness_status": item.faithfulness_status,
        "created_at": item.created_at.isoformat(),
    }


def _citation_payload(item: CitationRecord) -> dict[str, Any]:
    return {
        "id": item.id, "answer_id": item.answer_id, "document_chunk_id": item.document_chunk_id,
        "citation_label": item.citation_label, "valid": item.valid, "created_at": item.created_at.isoformat(),
    }


def _retrieval_run_payload(item: RetrievalRunRecord) -> dict[str, Any]:
    return {
        "id": item.id, "answer_id": item.answer_id, "organization_id": item.organization_id,
        "query_text": item.query_text, "retrieval_mode": item.retrieval_mode,
        "dense_count": item.dense_count, "bm25_count": item.bm25_count,
        "fused_count": item.fused_count, "reranked_count": item.reranked_count,
        "retrieval_latency_ms": item.retrieval_latency_ms, "rerank_latency_ms": item.rerank_latency_ms,
        "generation_latency_ms": item.generation_latency_ms, "verification_latency_ms": item.verification_latency_ms,
        "total_latency_ms": item.total_latency_ms, "input_tokens": item.input_tokens,
        "output_tokens": item.output_tokens, "estimated_cost": item.estimated_cost,
        "created_at": item.created_at.isoformat(),
    }


