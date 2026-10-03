from fastapi.testclient import TestClient

from app.api.main import app
from app.auth.service import AuthenticatedPrincipal


def test_auth_me_rejects_missing_token():
    with TestClient(app) as client:
        response = client.get("/auth/me")
    assert response.status_code in {401, 503}


def test_auth_me_accepts_verified_principal(monkeypatch):
    import app.api.main as main

    class FakeAuth:
        def authenticate_bearer(self, authorization):
            assert authorization == "Bearer test-token"
            return AuthenticatedPrincipal(user_id="user-a", role="authenticated", claims={})

    monkeypatch.setattr(main, "_auth_service", lambda token: FakeAuth())
    with TestClient(app) as client:
        response = client.get("/auth/me", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json() == {"user_id": "user-a", "role": "authenticated"}


def test_document_upload_rejects_non_pdf_before_storage(monkeypatch):
    import app.api.main as main

    principal = AuthenticatedPrincipal(
        user_id="user-a",
        role="authenticated",
        claims={},
    )

    class UnusedClient:
        pass

    app.dependency_overrides[main.current_user_client] = (
        lambda: (principal, UnusedClient())
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/documents",
                files={"file": ("notes.txt", b"not a pdf", "text/plain")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415


def test_document_status_returns_authenticated_document(monkeypatch):
    import app.api.main as main
    from app.persistence.entities import DocumentRecord, IngestionJobRecord

    principal = AuthenticatedPrincipal(
        user_id="user-a",
        role="authenticated",
        claims={},
    )

    class FakeResponse:
        data = [{"organization_id": "org-a"}]
        error = None

    class FakeClient:
        def table(self, name):
            assert name == "organization_members"
            return self

        def select(self, value):
            return self

        def eq(self, key, value):
            return self

        def execute(self):
            return FakeResponse()

    document = DocumentRecord(
        id="doc-a",
        organization_id="org-a",
        owner_user_id="user-a",
        filename="handbook.pdf",
        storage_path="organizations/org-a/documents/doc-a/handbook.pdf",
        content_hash="a" * 64,
        pipeline_version="v1",
    )
    job = IngestionJobRecord(
        id="job-a",
        organization_id="org-a",
        document_id="doc-a",
        pipeline_version="v1",
        content_hash="a" * 64,
    )

    class FakeDocuments:
        def __init__(self, client):
            pass

        def get(self, document_id, organization_id):
            assert (document_id, organization_id) == ("doc-a", "org-a")
            return document

    class FakeJobs:
        def __init__(self, client):
            pass

        def get_by_document(self, document_id, organization_id):
            assert (document_id, organization_id) == ("doc-a", "org-a")
            return job

    monkeypatch.setattr(main, "SupabaseDocumentRepository", FakeDocuments)
    monkeypatch.setattr(main, "SupabaseIngestionJobRepository", FakeJobs)
    app.dependency_overrides[main.current_user_client] = (
        lambda: (principal, FakeClient())
    )
    try:
        with TestClient(app) as client:
            response = client.get("/documents/doc-a")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["document_id"] == "doc-a"
    assert response.json()["ingestion_job_id"] == "job-a"
    assert response.json()["status"] == "UPLOADED"


def test_readiness_rejects_unloaded_pipeline(monkeypatch):
    import app.api.main as main

    monkeypatch.setattr(main, "pipeline", None)
    try:
        main.readiness()
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 503
    else:
        raise AssertionError("readiness() should reject an unloaded pipeline")


def test_readiness_accepts_loaded_pipeline(monkeypatch):
    import app.api.main as main

    monkeypatch.setattr(main, "pipeline", object())
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
