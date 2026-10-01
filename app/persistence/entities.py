from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class DocumentRecord:
    id: str
    organization_id: str
    owner_user_id: str
    filename: str
    storage_path: str
    content_hash: str
    pipeline_version: str
    status: str = "UPLOADED"
    page_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class IngestionJobRecord:
    id: str
    organization_id: str
    document_id: str
    status: str = "PENDING"
    pipeline_version: str = ""
    content_hash: str = ""
    attempt_count: int = 0
    lease_until: datetime | None = None
    last_error: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ConversationRecord:
    id: str
    organization_id: str
    user_id: str
    title: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class MessageRecord:
    id: str
    conversation_id: str
    user_id: str
    role: str
    content: str
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class AnswerRecord:
    id: str
    message_id: str
    query_text: str
    answer_text: str
    retrieval_mode: str
    rewritten_query: str | None = None
    faithfulness_status: str | None = None
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class CitationRecord:
    id: str
    answer_id: str
    document_chunk_id: str
    citation_label: str
    valid: bool = False
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class RetrievalRunRecord:
    id: str
    answer_id: str
    organization_id: str
    query_text: str
    retrieval_mode: str
    dense_count: int = 0
    bm25_count: int = 0
    fused_count: int = 0
    reranked_count: int = 0
    retrieval_latency_ms: float | None = None
    rerank_latency_ms: float | None = None
    generation_latency_ms: float | None = None
    verification_latency_ms: float | None = None
    total_latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    created_at: datetime = field(default_factory=utcnow)
