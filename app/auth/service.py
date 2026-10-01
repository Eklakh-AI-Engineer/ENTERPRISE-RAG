from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class InvalidTokenError(ValueError):
    """Raised when a caller cannot be authenticated."""


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    user_id: str
    role: str
    claims: dict[str, Any]


class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedPrincipal: ...


class SupabaseTokenVerifier:
    """Adapter around Supabase's verified-claims API.

    The Supabase Python client verifies the access-token JWT before returning
    claims. This class deliberately does not decode JWTs itself.
    """

    def __init__(self, client: Any) -> None:
        self.client = client

    def verify(self, token: str) -> AuthenticatedPrincipal:
        if not token.strip():
            raise InvalidTokenError("Missing access token")
        try:
            response = self.client.auth.get_claims(token)
        except Exception as exc:
            raise InvalidTokenError("Invalid access token") from exc

        error = getattr(response, "error", None)
        if error:
            raise InvalidTokenError("Invalid access token")
        data = getattr(response, "data", None)
        claims = getattr(data, "claims", None)
        if claims is None and isinstance(data, dict):
            claims = data.get("claims")
        if not isinstance(claims, dict):
            raise InvalidTokenError("Verified token claims are unavailable")

        user_id = claims.get("sub")
        role = claims.get("role")
        if not isinstance(user_id, str) or not user_id:
            raise InvalidTokenError("Token does not contain a user subject")
        if not isinstance(role, str) or role != "authenticated":
            raise InvalidTokenError("Token does not have the authenticated role")
        return AuthenticatedPrincipal(user_id=user_id, role=role, claims=dict(claims))


class AuthService:
    """Application authentication boundary; authorization remains resource-scoped."""

    def __init__(self, verifier: TokenVerifier) -> None:
        self.verifier = verifier

    def authenticate_bearer(self, authorization: str | None) -> AuthenticatedPrincipal:
        if not authorization:
            raise InvalidTokenError("Missing Authorization header")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise InvalidTokenError("Authorization must use Bearer token")
        return self.verifier.verify(token.strip())
