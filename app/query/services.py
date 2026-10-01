from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.persistence.entities import (
    AnswerRecord,
    CitationRecord,
    ConversationRecord,
    MessageRecord,
    RetrievalRunRecord,
)
from app.persistence.repositories import AnswerRepository, ConversationRepository


class QueryValidationError(ValueError):
    """Raised when a persisted query violates the application contract."""


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    message: MessageRecord
    answer: AnswerRecord


class ConversationService:
    """Authenticated conversation persistence boundary.

    Retrieval/generation remains elsewhere. This service owns identity,
    ownership checks, and durable relationships between messages and answers.
    """

    def __init__(self, conversations: ConversationRepository) -> None:
        self.conversations = conversations

    def create(self, *, organization_id: str, user_id: str, title: str | None = None) -> ConversationRecord:
        if not organization_id.strip() or not user_id.strip():
            raise QueryValidationError("organization_id and user_id are required")
        conversation = ConversationRecord(
            id=str(uuid4()), organization_id=organization_id, user_id=user_id, title=title
        )
        return self.conversations.save(conversation)

    def get(self, *, conversation_id: str, user_id: str) -> ConversationRecord:
        conversation = self.conversations.get(conversation_id, user_id)
        if conversation is None:
            raise KeyError("Conversation not found")
        return conversation

    def add_user_message(self, *, conversation_id: str, user_id: str, content: str) -> MessageRecord:
        if not content.strip():
            raise QueryValidationError("message content is required")
        self.get(conversation_id=conversation_id, user_id=user_id)
        return self.conversations.add_message(
            MessageRecord(
                id=str(uuid4()), conversation_id=conversation_id, user_id=user_id,
                role="user", content=content,
            )
        )


class AnswerPersistenceService:
    """Persistence boundary for generated answers and evidence telemetry."""

    def __init__(self, answers: AnswerRepository) -> None:
        self.answers = answers

    def save_turn(
        self,
        *,
        message: MessageRecord,
        query_text: str,
        answer_text: str,
        retrieval_mode: str,
        rewritten_query: str | None = None,
        faithfulness_status: str | None = None,
        citations: list[CitationRecord] | None = None,
        retrieval_run: RetrievalRunRecord | None = None,
    ) -> AnswerRecord:
        if message.role != "user":
            raise QueryValidationError("answer must be attached to a user query message")
        if not query_text.strip() or not answer_text.strip():
            raise QueryValidationError("query_text and answer_text are required")
        answer = AnswerRecord(
            id=str(uuid4()), message_id=message.id, query_text=query_text,
            answer_text=answer_text, retrieval_mode=retrieval_mode,
            rewritten_query=rewritten_query, faithfulness_status=faithfulness_status,
        )
        self.answers.save_answer(answer)
        for citation in citations or []:
            if citation.answer_id != answer.id:
                raise QueryValidationError("citation answer_id must match persisted answer")
            self.answers.save_citation(citation)
        if retrieval_run is not None:
            if retrieval_run.answer_id != answer.id:
                raise QueryValidationError("retrieval_run answer_id must match persisted answer")
            self.answers.save_retrieval_run(retrieval_run)
        return answer
