import pytest

from app.auth.service import AuthService, InvalidTokenError, SupabaseTokenVerifier


class FakeUser:
    def __init__(self, user_id="user-a", role="authenticated"):
        self.id = user_id
        self.role = role
        self.user_metadata = {"name": "Test User"}
        self.app_metadata = {"provider": "email"}


class Response:
    def __init__(self, user=None, error=None):
        self.user = user
        self.error = error


class FakeAuth:
    def __init__(self, response):
        self.response = response

    def get_user(self, token):
        assert token == "valid-token"
        return self.response


class FakeClient:
    def __init__(self, response):
        self.auth = FakeAuth(response)


def test_verified_supabase_user_produces_principal():
    verifier = SupabaseTokenVerifier(
        FakeClient(Response(FakeUser()))
    )
    principal = AuthService(verifier).authenticate_bearer("Bearer valid-token")
    assert principal.user_id == "user-a"
    assert principal.role == "authenticated"
    assert principal.claims["sub"] == "user-a"


def test_missing_bearer_token_is_rejected():
    verifier = SupabaseTokenVerifier(FakeClient(Response(FakeUser())))
    with pytest.raises(InvalidTokenError):
        AuthService(verifier).authenticate_bearer(None)


def test_wrong_role_is_rejected():
    verifier = SupabaseTokenVerifier(
        FakeClient(Response(FakeUser(role="anon")))
    )
    with pytest.raises(InvalidTokenError):
        AuthService(verifier).authenticate_bearer("Bearer valid-token")


def test_verifier_rejects_missing_user():
    verifier = SupabaseTokenVerifier(FakeClient(Response(None)))
    with pytest.raises(InvalidTokenError):
        verifier.verify("valid-token")


def test_verifier_rejects_auth_error():
    verifier = SupabaseTokenVerifier(
        FakeClient(Response(error={"message": "invalid token"}))
    )
    with pytest.raises(InvalidTokenError):
        verifier.verify("valid-token")
