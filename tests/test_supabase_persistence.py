from datetime import datetime, timezone

from app.persistence.entities import DocumentRecord, IngestionJobRecord
from app.persistence.supabase import (
    SupabaseDocumentRepository,
    SupabaseIngestionJobRepository,
)


class Response:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []

    def select(self, *_):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def maybe_single(self):
        return self

    def single(self):
        return self

    def upsert(self, *_args, **_kwargs):
        return self

    def insert(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = [
            row for row in self.rows
            if all(row.get(k) == v for k, v in self.filters)
        ]
        return Response(rows[0] if rows else None)


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def table(self, name):
        self.calls.append(("table", name))
        return Query(self.rows)

    def rpc(self, name, params):
        self.calls.append(("rpc", name, params))
        return Query(self.rows)


def test_document_adapter_preserves_tenant_filter():
    row = {
        "id": "doc-1",
        "organization_id": "org-a",
        "owner_user_id": "user-a",
        "filename": "policy.pdf",
        "storage_path": "org-a/doc-1/policy.pdf",
        "content_hash": "hash",
        "pipeline_version": "v1",
        "status": "UPLOADED",
        "metadata": {},
        "created_at": "2026-10-01T00:00:00+00:00",
        "updated_at": "2026-10-01T00:00:00+00:00",
    }
    repo = SupabaseDocumentRepository(FakeClient([row]))

    assert repo.get("doc-1", "org-a").organization_id == "org-a"
    assert repo.get("doc-1", "org-b") is None


def test_job_adapter_maps_lease_and_attempts():
    row = {
        "id": "job-1",
        "organization_id": "org-a",
        "document_id": "doc-1",
        "status": "PROCESSING",
        "pipeline_version": "v1",
        "content_hash": "hash",
        "attempt_count": 2,
        "lease_until": "2026-10-01T00:05:00+00:00",
        "last_error": None,
        "created_at": "2026-10-01T00:00:00+00:00",
        "updated_at": "2026-10-01T00:01:00+00:00",
    }
    repo = SupabaseIngestionJobRepository(FakeClient([row]))
    job = repo.get("job-1", "org-a")

    assert job.attempt_count == 2
    assert job.lease_until == datetime(2026, 10, 1, 0, 5, tzinfo=timezone.utc)
