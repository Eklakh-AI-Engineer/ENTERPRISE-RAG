import pytest

from app.auth.service import AuthService, InvalidTokenError, SupabaseTokenVerifier


class Response:
    def __init__(self, claims=None, error=None):
        self.data = type("Data", (), {"claims": claims})() if claims is not None else None
        self.error = error


class FakeAuth:
    def __init__(self, response):
        self.response = response
    def get_claims(self, token):
        assert token == "valid-token"
        return self.response


class FakeClient:
    def __init__(self, response):
        self.auth = FakeAuth(response)


def test_verified_supabase_claims_produce_principal():
    verifier = SupabaseTokenVerifier(FakeClient(Response({"sub": "user-a", "role": "authenticated"})))
    principal = AuthService(verifier).authenticate_bearer("Bearer valid-token")
    assert principal.user_id == "user-a"
    assert principal.role == "authenticated"


def test_missing_bearer_token_is_rejected():
    verifier = SupabaseTokenVerifier(FakeClient(Response({"sub": "user-a", "role": "authenticated"})))
    with pytest.raises(InvalidTokenError):
        AuthService(verifier).authenticate_bearer(None)


def test_wrong_role_is_rejected():
    verifier = SupabaseTokenVerifier(FakeClient(Response({"sub": "user-a", "role": "anon"})))
    with pytest.raises(InvalidTokenError):
        AuthService(verifier).authenticate_bearer("Bearer valid-token")


def test_verifier_does_not_accept_missing_claims():
    verifier = SupabaseTokenVerifier(FakeClient(Response({"role": "authenticated"})))
    with pytest.raises(InvalidTokenError):
        verifier.verify("valid-token")
