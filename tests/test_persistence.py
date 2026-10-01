from app.persistence.entities import (
    ConversationRecord,
    DocumentRecord,
    IngestionJobRecord,
    MessageRecord,
)
from app.persistence.in_memory import (
    InMemoryConversationRepository,
    InMemoryDocumentRepository,
    InMemoryIngestionJobRepository,
)


def test_document_content_hash_lookup_is_tenant_scoped():
    repo = InMemoryDocumentRepository()

    repo.save(
        DocumentRecord(
            id="doc-a",
            organization_id="org-a",
            owner_user_id="user-a",
            filename="policy.pdf",
            storage_path="org-a/policy.pdf",
            content_hash="hash-1",
            pipeline_version="v1",
        )
    )

    assert repo.get_by_content("org-a", "hash-1", "v1") is not None
    assert repo.get_by_content("org-b", "hash-1", "v1") is None


def test_ingestion_job_lifecycle_is_explicit():
    repo = InMemoryIngestionJobRepository()
    job = IngestionJobRecord(
        id="job-1",
        organization_id="org-a",
        document_id="doc-a",
        pipeline_version="v1",
        content_hash="hash-1",
    )

    repo.create(job)
    job.status = "PROCESSING"
    repo.update(job)

    assert repo.get("job-1", "org-a").status == "PROCESSING"


def test_message_cannot_cross_conversation_owner_boundary():
    repo = InMemoryConversationRepository()
    repo.save(
        ConversationRecord(
            id="conv-1",
            organization_id="org-a",
            user_id="user-a",
        )
    )

    try:
        repo.add_message(
            MessageRecord(
                id="msg-1",
                conversation_id="conv-1",
                user_id="user-b",
                role="user",
                content="cross-tenant attempt",
            )
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("Cross-owner message must be rejected.")
