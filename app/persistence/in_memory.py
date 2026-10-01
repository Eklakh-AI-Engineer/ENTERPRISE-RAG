from app.persistence.entities import (
    AnswerRecord,
    CitationRecord,
    ConversationRecord,
    DocumentRecord,
    IngestionJobRecord,
    MessageRecord,
    RetrievalRunRecord,
)


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self._items: dict[str, DocumentRecord] = {}

    def get(self, document_id: str, organization_id: str):
        item = self._items.get(document_id)
        if item and item.organization_id == organization_id:
            return item
        return None

    def get_by_content(self, organization_id: str, content_hash: str, pipeline_version: str):
        for item in self._items.values():
            if (
                item.organization_id == organization_id
                and item.content_hash == content_hash
                and item.pipeline_version == pipeline_version
            ):
                return item
        return None

    def save(self, document: DocumentRecord):
        self._items[document.id] = document
        return document


class InMemoryIngestionJobRepository:
    def __init__(self) -> None:
        self._items: dict[str, IngestionJobRecord] = {}

    def get(self, job_id: str, organization_id: str):
        item = self._items.get(job_id)
        if item and item.organization_id == organization_id:
            return item
        return None

    def create(self, job: IngestionJobRecord):
        if job.id in self._items:
            raise ValueError(f"Ingestion job already exists: {job.id}")
        self._items[job.id] = job
        return job

    def update(self, job: IngestionJobRecord):
        if job.id not in self._items:
            raise KeyError(f"Unknown ingestion job: {job.id}")
        self._items[job.id] = job
        return job


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._conversations: dict[str, ConversationRecord] = {}
        self._messages: dict[str, MessageRecord] = {}

    def get(self, conversation_id: str, user_id: str):
        item = self._conversations.get(conversation_id)
        if item and item.user_id == user_id:
            return item
        return None

    def save(self, conversation: ConversationRecord):
        self._conversations[conversation.id] = conversation
        return conversation

    def add_message(self, message: MessageRecord):
        conversation = self._conversations.get(message.conversation_id)
        if conversation is None or conversation.user_id != message.user_id:
            raise PermissionError("Message owner does not match conversation owner.")
        self._messages[message.id] = message
        return message


class InMemoryAnswerRepository:
    def __init__(self) -> None:
        self.answers: dict[str, AnswerRecord] = {}
        self.citations: dict[str, CitationRecord] = {}
        self.retrieval_runs: dict[str, RetrievalRunRecord] = {}

    def save_answer(self, answer: AnswerRecord):
        self.answers[answer.id] = answer
        return answer

    def save_citation(self, citation: CitationRecord):
        self.citations[citation.id] = citation
        return citation

    def save_retrieval_run(self, run: RetrievalRunRecord):
        self.retrieval_runs[run.id] = run
        return run
