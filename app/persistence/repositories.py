from typing import Protocol

from app.persistence.entities import (
    AnswerRecord,
    CitationRecord,
    ConversationRecord,
    DocumentRecord,
    IngestionJobRecord,
    MessageRecord,
    RetrievalRunRecord,
)


class DocumentRepository(Protocol):
    def get(self, document_id: str, organization_id: str) -> DocumentRecord | None: ...
    def get_by_content(
        self,
        organization_id: str,
        content_hash: str,
        pipeline_version: str,
    ) -> DocumentRecord | None: ...
    def save(self, document: DocumentRecord) -> DocumentRecord: ...


class IngestionJobRepository(Protocol):
    def get(self, job_id: str, organization_id: str) -> IngestionJobRecord | None: ...
    def create(self, job: IngestionJobRecord) -> IngestionJobRecord: ...
    def update(self, job: IngestionJobRecord) -> IngestionJobRecord: ...


class ConversationRepository(Protocol):
    def get(self, conversation_id: str, user_id: str) -> ConversationRecord | None: ...
    def save(self, conversation: ConversationRecord) -> ConversationRecord: ...
    def add_message(self, message: MessageRecord) -> MessageRecord: ...


class AnswerRepository(Protocol):
    def save_answer(self, answer: AnswerRecord) -> AnswerRecord: ...
    def save_citation(self, citation: CitationRecord) -> CitationRecord: ...
    def save_retrieval_run(self, run: RetrievalRunRecord) -> RetrievalRunRecord: ...
