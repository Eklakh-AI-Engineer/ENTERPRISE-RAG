from __future__ import annotations

from typing import Any

from supabase import create_client

from app.config.settings import settings


class SupabaseConfigurationError(RuntimeError):
    """Raised when required Supabase runtime configuration is missing."""


def _require(value: str, name: str) -> str:
    if not value.strip():
        raise SupabaseConfigurationError(f"{name} is required")
    return value


def create_user_client(*, access_token: str | None = None) -> Any:
    """Create a Supabase client for authenticated user-scoped operations."""
    client = create_client(
        _require(settings.SUPABASE_URL, "SUPABASE_URL"),
        _require(settings.SUPABASE_PUBLISHABLE_KEY, "SUPABASE_PUBLISHABLE_KEY"),
    )
    if access_token:
        client.postgrest.auth(access_token)
    return client


def create_service_client() -> Any:
    """Create a trusted worker client; never expose its key to the frontend."""
    return create_client(
        _require(settings.SUPABASE_URL, "SUPABASE_URL"),
        _require(settings.SUPABASE_SERVICE_ROLE_KEY, "SUPABASE_SERVICE_ROLE_KEY"),
    )
