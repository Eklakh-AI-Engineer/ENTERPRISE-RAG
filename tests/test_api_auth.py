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

    monkeypatch.setattr(main, "_auth_service", lambda: FakeAuth())
    with TestClient(app) as client:
        response = client.get("/auth/me", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json() == {"user_id": "user-a", "role": "authenticated"}
