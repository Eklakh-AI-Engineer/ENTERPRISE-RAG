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
    """Verify Supabase Auth access tokens through the supported Auth API."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def verify(self, token: str) -> AuthenticatedPrincipal:
        if not token.strip():
            raise InvalidTokenError("Missing access token")

        try:
            response = self.client.auth.get_user(token.strip())
        except Exception as exc:
            raise InvalidTokenError("Invalid access token") from exc

        if response is None:
            raise InvalidTokenError("Authenticated user was not returned")

        error = getattr(response, "error", None)
        if error:
            raise InvalidTokenError("Invalid access token")

        user = getattr(response, "user", None)
        user_id = getattr(user, "id", None)
        role = getattr(user, "role", None) or "authenticated"

        if not isinstance(user_id, str) or not user_id:
            raise InvalidTokenError("Authenticated user does not contain an id")

        if role != "authenticated":
            raise InvalidTokenError("Token does not have the authenticated role")

        claims = {
            "sub": user_id,
            "role": role,
        }

        user_metadata = getattr(user, "user_metadata", None)
        app_metadata = getattr(user, "app_metadata", None)
        if isinstance(user_metadata, dict):
            claims["user_metadata"] = user_metadata
        if isinstance(app_metadata, dict):
            claims["app_metadata"] = app_metadata

        return AuthenticatedPrincipal(
            user_id=user_id,
            role="authenticated",
            claims=claims,
        )


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
