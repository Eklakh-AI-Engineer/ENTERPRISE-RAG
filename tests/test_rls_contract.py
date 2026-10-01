from pathlib import Path


SCHEMA = Path("supabase/schema.sql").read_text(encoding="utf-8")


def _policy(name_fragment: str) -> str:
    marker = f'create policy "{name_fragment}"'
    start = SCHEMA.index(marker)
    next_start = SCHEMA.find("create policy \\\"", start + len(marker))
    return SCHEMA[start: next_start if next_start != -1 else len(SCHEMA)]


def test_rls_enabled_for_user_data_tables():
    for table in (
        "organizations", "organization_members", "documents", "document_chunks",
        "ingestion_jobs", "conversations", "messages", "answers", "citations", "retrieval_runs",
    ):
        assert f"alter table public.{table} enable row level security;" in SCHEMA


def test_documents_are_membership_scoped():
    section = _policy("members can read documents")
    assert "organization_members" in section
    assert "auth.uid()" in section


def test_conversations_are_user_scoped():
    section = _policy("users can read their conversations")
    assert "auth.uid()" in section


def test_chunks_do_not_bypass_document_tenant_boundary():
    section = _policy("members can read document chunks")
    assert "documents d" in section
    assert "organization_members" in section


def test_service_role_is_not_granted_atomic_claim_to_public_roles():
    assert "revoke execute on function public.claim_ingestion_job(uuid, integer) from authenticated;" in SCHEMA
    assert "grant execute on function public.claim_ingestion_job(uuid, integer) to service_role;" in SCHEMA


def test_storage_bucket_is_private_and_tenant_scoped():
    assert "values ('documents', 'documents', false)" in SCHEMA
    assert "split_part(name, '/', 2)::uuid" in SCHEMA
    assert 'on storage.objects' in SCHEMA


def test_retrieval_run_policy_uses_answer_alias():
    section = _policy("users can read their retrieval runs")
    assert "a.id = retrieval_runs.answer_id" in section
    assert "answers.message_id" not in section
    assert "m.id = a.message_id" in section



def test_claim_function_has_valid_dollar_quoted_body():
    start = SCHEMA.index("create or replace function public.claim_ingestion_job")
    end = SCHEMA.index("-- Invoker function:", start)
    section = SCHEMA[start:end]
    assert "as $$" in section
    assert "declare" in section
    assert "$$;" in section
