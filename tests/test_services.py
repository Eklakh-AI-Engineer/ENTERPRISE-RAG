from datetime import timedelta

import pytest

from app.persistence.in_memory import (
    InMemoryDocumentRepository,
    InMemoryIngestionJobRepository,
)
from app.persistence.entities import utcnow
from app.services.documents import DocumentService, DocumentValidationError
from app.services.ingestion import IngestionService, IngestionStateError


def make_services():
    docs = InMemoryDocumentRepository()
    jobs = InMemoryIngestionJobRepository()
    return (
        DocumentService(docs, jobs),
        IngestionService(jobs),
        docs,
        jobs,
    )


def test_document_submission_hashes_content_and_creates_job():
    documents, _, _, _ = make_services()

    result = documents.submit(
        organization_id="org-a",
        owner_user_id="user-a",
        filename="policy.pdf",
        content=b"same bytes",
        pipeline_version="ingest-v1",
    )

    assert len(result.document.content_hash) == 64
    assert result.document.status == "UPLOADED"
    assert result.ingestion_job.status == "PENDING"
    assert result.deduplicated is False


def test_duplicate_content_is_tenant_scoped_and_idempotent():
    documents, _, _, _ = make_services()

    first = documents.submit(
        organization_id="org-a",
        owner_user_id="user-a",
        filename="policy.pdf",
        content=b"same bytes",
        pipeline_version="ingest-v1",
    )
    second = documents.submit(
        organization_id="org-a",
        owner_user_id="user-b",
        filename="renamed.pdf",
        content=b"same bytes",
        pipeline_version="ingest-v1",
    )
    other_tenant = documents.submit(
        organization_id="org-b",
        owner_user_id="user-c",
        filename="policy.pdf",
        content=b"same bytes",
        pipeline_version="ingest-v1",
    )

    assert second.deduplicated is True
    assert second.document.id == first.document.id
    assert other_tenant.deduplicated is False
    assert other_tenant.document.id != first.document.id


@pytest.mark.parametrize(
    "filename,content,pipeline",
    [
        ("", b"data", "v1"),
        ("../policy.pdf", b"data", "v1"),
        ("policy.pdf", b"", "v1"),
        ("policy.pdf", b"data", ""),
    ],
)
def test_document_input_validation(filename, content, pipeline):
    documents, _, _, _ = make_services()
    with pytest.raises(DocumentValidationError):
        documents.submit(
            organization_id="org-a",
            owner_user_id="user-a",
            filename=filename,
            content=content,
            pipeline_version=pipeline,
        )


def test_ingestion_claim_complete_and_retry_expired():
    _, ingestion, _, jobs = make_services()
    now = utcnow()
    result = DocumentService(
        _,
        jobs,
    ) if False else None

    from app.persistence.entities import IngestionJobRecord

    job = IngestionJobRecord(
        id="job-1",
        organization_id="org-a",
        document_id="doc-1",
        pipeline_version="v1",
        content_hash="hash",
    )
    jobs.create(job)

    claimed = ingestion.claim(
        job_id="job-1",
        organization_id="org-a",
        lease_seconds=60,
        now=now,
    )
    assert claimed.status == "PROCESSING"
    assert claimed.attempt_count == 1

    with pytest.raises(IngestionStateError):
        ingestion.claim(
            job_id="job-1",
            organization_id="org-a",
            lease_seconds=60,
            now=now + timedelta(seconds=30),
        )

    expired = ingestion.retry_expired(
        job_id="job-1",
        organization_id="org-a",
        now=now + timedelta(seconds=61),
    )
    assert expired.status == "PENDING"

    claimed_again = ingestion.claim(
        job_id="job-1",
        organization_id="org-a",
        lease_seconds=60,
        now=now + timedelta(seconds=62),
    )
    assert claimed_again.attempt_count == 2

    completed = ingestion.complete(
        job_id="job-1",
        organization_id="org-a",
        now=now + timedelta(seconds=63),
    )
    assert completed.status == "READY"
    assert completed.lease_until is None


def test_failed_job_records_error_and_can_be_reclaimed():
    _, ingestion, _, jobs = make_services()
    from app.persistence.entities import IngestionJobRecord

    jobs.create(
        IngestionJobRecord(
            id="job-2",
            organization_id="org-a",
            document_id="doc-2",
            pipeline_version="v1",
            content_hash="hash",
        )
    )
    ingestion.claim(job_id="job-2", organization_id="org-a")
    failed = ingestion.fail(
        job_id="job-2",
        organization_id="org-a",
        error="OCR failed",
    )
    assert failed.status == "FAILED"
    assert failed.last_error == "OCR failed"

    reclaimed = ingestion.claim(job_id="job-2", organization_id="org-a")
    assert reclaimed.status == "PROCESSING"
    assert reclaimed.attempt_count == 2
