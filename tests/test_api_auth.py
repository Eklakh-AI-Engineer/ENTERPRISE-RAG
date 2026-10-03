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
