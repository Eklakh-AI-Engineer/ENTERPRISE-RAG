from pathlib import Path


SCHEMA = Path("supabase/schema.sql").read_text(encoding="utf-8")


def _section(table: str) -> str:
    marker = f"alter table public.{table} enable row level security;"
    start = SCHEMA.index(marker)
    next_start = SCHEMA.find("alter table public.", start + len(marker))
    return SCHEMA[start: next_start if next_start != -1 else len(SCHEMA)]


def test_rls_enabled_for_user_data_tables():
    for table in (
        "organizations", "organization_members", "documents", "document_chunks",
        "ingestion_jobs", "conversations", "messages", "answers", "citations", "retrieval_runs",
    ):
        assert f"alter table public.{table} enable row level security;" in SCHEMA


def test_documents_are_membership_scoped():
    section = _section("documents")
    assert "organization_members" in section
    assert "auth.uid()" in section


def test_conversations_are_user_scoped():
    section = _section("conversations")
    assert "auth.uid()" in section


def test_chunks_do_not_bypass_document_tenant_boundary():
    section = _section("document_chunks")
    assert "documents d" in section
    assert "organization_members" in section


def test_service_role_is_not_granted_atomic_claim_to_public_roles():
    assert "revoke execute on function public.claim_ingestion_job(uuid, integer) from authenticated;" in SCHEMA
    assert "grant execute on function public.claim_ingestion_job(uuid, integer) to service_role;" in SCHEMA
