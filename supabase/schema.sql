-- Enterprise RAG canonical database schema
-- STATUS: mirrors the dedicated Enterprise-RAG Supabase project plus the
-- repository migration history. New production changes must be added as
-- versioned migrations and reflected here after verification.
--
-- This file is a canonical schema contract for review and CI. It is not a
-- substitute for applying versioned migrations to the live project.
--
-- Current retrieval baseline:
--   embedding model: sentence-transformers/all-MiniLM-L6-v2
--   dimension: 384
--   FAISS baseline uses normalized embeddings
--   pgvector parity metric: cosine distance (<=>)
--
-- Supabase currently recommends the vector extension in the extensions schema.
-- See docs/DATABASE.md for the production decision gates.

create extension if not exists vector with schema extensions;

create table public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(trim(name)) > 0),
  created_at timestamptz not null default now()
);

create table public.organization_members (
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member'
    check (role in ('owner', 'admin', 'member')),
  created_at timestamptz not null default now(),
  primary key (organization_id, user_id)
);

create index organization_members_user_idx
  on public.organization_members (user_id, organization_id);

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete restrict,
  filename text not null check (length(trim(filename)) > 0),
  storage_path text not null,
  content_hash text not null,
  pipeline_version text not null,
  status text not null default 'UPLOADED'
    check (status in ('UPLOADED', 'PROCESSING', 'INDEXING', 'READY', 'FAILED')),
  page_count integer check (page_count is null or page_count >= 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, content_hash, pipeline_version)
);

create index documents_org_idx
  on public.documents (organization_id);

alter table public.documents
  add constraint documents_organization_id_id_key unique (organization_id, id);

create index documents_owner_idx
  on public.documents (owner_user_id);

create table public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_id text not null,
  content text not null,
  page integer not null check (page >= 1),
  section text,
  start_char integer check (start_char is null or start_char >= 0),
  end_char integer check (end_char is null or end_char >= 0),
  chunker_version text not null,
  embedding_model text not null,
  embedding_dimension integer not null check (embedding_dimension > 0),
  embedding extensions.vector(384),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (document_id, chunk_id, chunker_version),
  check (
    start_char is null
    or end_char is null
    or end_char >= start_char
  ),
  check (
    embedding is null
    or embedding_dimension = 384
  )
);

create index document_chunks_document_idx
  on public.document_chunks (document_id);

-- Current baseline parity index. Do not treat this as final production tuning
-- until the FAISS-vs-pgvector parity benchmark is complete.
create index document_chunks_embedding_hnsw_idx
  on public.document_chunks
  using hnsw (embedding vector_cosine_ops);

create table public.ingestion_jobs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  status text not null default 'PENDING'
    check (status in ('PENDING', 'PROCESSING', 'READY', 'FAILED')),
  pipeline_version text not null,
  content_hash text not null,
  attempt_count integer not null default 0 check (attempt_count >= 0),
  lease_until timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (document_id, content_hash, pipeline_version)
);

alter table public.ingestion_jobs
  add constraint ingestion_jobs_document_org_fkey
  foreign key (organization_id, document_id)
  references public.documents (organization_id, id)
  on delete cascade;

create index ingestion_jobs_worker_idx
  on public.ingestion_jobs (status, lease_until, created_at);

create index ingestion_jobs_org_idx
  on public.ingestion_jobs (organization_id);

create policy "members can create ingestion jobs"
on public.ingestion_jobs
for insert
to authenticated
with check (
  exists (
    select 1
    from public.organization_members om
    join public.documents d
      on d.id = ingestion_jobs.document_id
     and d.organization_id = ingestion_jobs.organization_id
    where om.organization_id = ingestion_jobs.organization_id
      and om.user_id = (select auth.uid())
  )
);

create policy "members can delete ingestion jobs"
on public.ingestion_jobs
for delete
to authenticated
using (
  exists (
    select 1
    from public.organization_members om
    where om.organization_id = ingestion_jobs.organization_id
      and om.user_id = (select auth.uid())
  )
);

create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index conversations_user_idx
  on public.conversations (user_id, updated_at desc);

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('system', 'user', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

create index messages_conversation_idx
  on public.messages (conversation_id, created_at);

create table public.answers (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages(id) on delete cascade,
  query_text text not null,
  rewritten_query text,
  answer_text text not null,
  retrieval_mode text not null,
  faithfulness_status text,
  created_at timestamptz not null default now()
);

create index answers_message_idx
  on public.answers (message_id);

create table public.citations (
  id uuid primary key default gen_random_uuid(),
  answer_id uuid not null references public.answers(id) on delete cascade,
  document_chunk_id uuid not null references public.document_chunks(id) on delete restrict,
  citation_label text not null,
  valid boolean not null default false,
  created_at timestamptz not null default now(),
  unique (answer_id, document_chunk_id, citation_label)
);

create index citations_answer_idx
  on public.citations (answer_id);

create table public.retrieval_runs (
  id uuid primary key default gen_random_uuid(),
  answer_id uuid not null references public.answers(id) on delete cascade,
  organization_id uuid not null references public.organizations(id) on delete cascade,
  query_text text not null,
  retrieval_mode text not null,
  dense_count integer not null default 0 check (dense_count >= 0),
  bm25_count integer not null default 0 check (bm25_count >= 0),
  fused_count integer not null default 0 check (fused_count >= 0),
  reranked_count integer not null default 0 check (reranked_count >= 0),
  retrieval_latency_ms numeric,
  rerank_latency_ms numeric,
  generation_latency_ms numeric,
  verification_latency_ms numeric,
  total_latency_ms numeric,
  input_tokens integer,
  output_tokens integer,
  estimated_cost numeric,
  created_at timestamptz not null default now()
);

create index retrieval_runs_org_idx
  on public.retrieval_runs (organization_id, created_at desc);

create index retrieval_runs_answer_idx
  on public.retrieval_runs (answer_id);

-- RLS: every exposed user-data table is protected.
alter table public.organizations enable row level security;
alter table public.organization_members enable row level security;
alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;
alter table public.ingestion_jobs enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.answers enable row level security;
alter table public.citations enable row level security;
alter table public.retrieval_runs enable row level security;

-- Explicit Data API grants. The 2026 Supabase platform change makes new
-- public-schema objects opt-in for Data API exposure, so grants are explicit.
grant select on public.organizations to authenticated;
grant select on public.organization_members to authenticated;
grant select, insert, update, delete on public.documents to authenticated;
grant select on public.document_chunks to authenticated;
grant select on public.ingestion_jobs to authenticated;
grant select, insert, update, delete on public.conversations to authenticated;
grant select, insert on public.messages to authenticated;
grant select on public.answers to authenticated;
grant select on public.citations to authenticated;
grant select on public.retrieval_runs to authenticated;

-- Membership visibility is limited to the caller's own memberships. Trusted
-- server-side operations create/update memberships.
create policy "members can read their own memberships"
on public.organization_members
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "members can read their organizations"
on public.organizations
for select
to authenticated
using (
  exists (
    select 1
    from public.organization_members om
    where om.organization_id = organizations.id
      and om.user_id = (select auth.uid())
  )
);

create policy "members can read documents"
on public.documents
for select
to authenticated
using (
  exists (
    select 1
    from public.organization_members om
    where om.organization_id = documents.organization_id
      and om.user_id = (select auth.uid())
  )
);

create policy "members can create their own documents"
on public.documents
for insert
to authenticated
with check (
  owner_user_id = (select auth.uid())
  and exists (
    select 1
    from public.organization_members om
    where om.organization_id = documents.organization_id
      and om.user_id = (select auth.uid())
  )
);

create policy "members can update documents"
on public.documents
for update
to authenticated
using (
  exists (
    select 1
    from public.organization_members om
    where om.organization_id = documents.organization_id
      and om.user_id = (select auth.uid())
  )
)
with check (
  exists (
    select 1
    from public.organization_members om
    where om.organization_id = documents.organization_id
      and om.user_id = (select auth.uid())
  )
  and owner_user_id = (select auth.uid())
);

create policy "members can delete documents"
on public.documents
for delete
to authenticated
using (
  exists (
    select 1
    from public.organization_members om
    where om.organization_id = documents.organization_id
      and om.user_id = (select auth.uid())
  )
);

create policy "members can read document chunks"
on public.document_chunks
for select
to authenticated
using (
  exists (
    select 1
    from public.documents d
    join public.organization_members om
      on om.organization_id = d.organization_id
    where d.id = document_chunks.document_id
      and om.user_id = (select auth.uid())
  )
);

create policy "members can read ingestion jobs"
on public.ingestion_jobs
for select
to authenticated
using (
  exists (
    select 1
    from public.organization_members om
    where om.organization_id = ingestion_jobs.organization_id
      and om.user_id = (select auth.uid())
  )
);

create policy "users can read their conversations"
on public.conversations
for select
to authenticated
using (
  user_id = (select auth.uid())
  and exists (
    select 1
    from public.organization_members om
    where om.organization_id = conversations.organization_id
      and om.user_id = (select auth.uid())
  )
);

create policy "users can create their conversations"
on public.conversations
for insert
to authenticated
with check (
  user_id = (select auth.uid())
  and exists (
    select 1
    from public.organization_members om
    where om.organization_id = conversations.organization_id
      and om.user_id = (select auth.uid())
  )
);

create policy "users can update their conversations"
on public.conversations
for update
to authenticated
using (user_id = (select auth.uid()))
with check (
  user_id = (select auth.uid())
  and exists (
    select 1
    from public.organization_members om
    where om.organization_id = conversations.organization_id
      and om.user_id = (select auth.uid())
  )
);

create policy "users can delete their conversations"
on public.conversations
for delete
to authenticated
using (user_id = (select auth.uid()));

create policy "users can read their messages"
on public.messages
for select
to authenticated
using (
  user_id = (select auth.uid())
  and exists (
    select 1
    from public.conversations c
    where c.id = messages.conversation_id
      and c.user_id = (select auth.uid())
  )
);

create policy "users can create their messages"
on public.messages
for insert
to authenticated
with check (
  user_id = (select auth.uid())
  and exists (
    select 1
    from public.conversations c
    where c.id = messages.conversation_id
      and c.user_id = (select auth.uid())
  )
);

create policy "users can read their answers"
on public.answers
for select
to authenticated
using (
  exists (
    select 1
    from public.messages m
    join public.conversations c on c.id = m.conversation_id
    where m.id = answers.message_id
      and c.user_id = (select auth.uid())
  )
);

create policy "users can read their citations"
on public.citations
for select
to authenticated
using (
  exists (
    select 1
    from public.answers a
    join public.messages m on m.id = a.message_id
    join public.conversations c on c.id = m.conversation_id
    where a.id = citations.answer_id
      and c.user_id = (select auth.uid())
  )
);

create policy "users can read their retrieval runs"
on public.retrieval_runs
for select
to authenticated
using (
  exists (
    select 1
    from public.answers a
    join public.messages m on m.id = a.message_id
    join public.conversations c on c.id = m.conversation_id
    where a.id = retrieval_runs.answer_id
      and c.user_id = (select auth.uid())
      and retrieval_runs.organization_id = c.organization_id
  )
);

-- Supabase Storage reference policies. The bucket/object path is tenant-scoped:
-- organizations/{organization_id}/documents/{document_id}/{filename}
-- These policies are part of the reference design and must be validated on the
-- dedicated project before accepting production files.
insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do nothing;

create policy "members can read organization documents"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'documents'
  and exists (
    select 1
    from public.organization_members om
    where om.organization_id = split_part(name, '/', 2)::uuid
      and om.user_id = (select auth.uid())
  )
);

create policy "members can upload organization documents"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'documents'
  and exists (
    select 1
    from public.organization_members om
    where om.organization_id = split_part(name, '/', 2)::uuid
      and om.user_id = (select auth.uid())
  )
  and split_part(name, '/', 1) = 'organizations'
  and split_part(name, '/', 3) = 'documents'
);

create policy "members can delete organization documents"
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'documents'
  and exists (
    select 1
    from public.organization_members om
    where om.organization_id = split_part(name, '/', 2)::uuid
      and om.user_id = (select auth.uid())
  )
);

create policy "ingestion jobs must match document tenant"
on public.ingestion_jobs
as restrictive
for insert
to authenticated
with check (
  exists (
    select 1
    from public.documents d
    where d.id = ingestion_jobs.document_id
      and d.organization_id = ingestion_jobs.organization_id
  )
);

create policy "storage objects must match document row"
on storage.objects
as restrictive
for all
to authenticated
using (
  bucket_id = 'documents'
  and split_part(name, '/', 1) = 'organizations'
  and split_part(name, '/', 3) = 'documents'
  and exists (
    select 1
    from public.documents d
    where d.organization_id = split_part(objects.name, '/', 2)::uuid
      and d.id = split_part(objects.name, '/', 4)::uuid
      and d.storage_path = objects.name
  )
)
with check (
  bucket_id = 'documents'
  and split_part(name, '/', 1) = 'organizations'
  and split_part(name, '/', 3) = 'documents'
  and exists (
    select 1
    from public.documents d
    where d.organization_id = split_part(name, '/', 2)::uuid
      and d.id = split_part(name, '/', 4)::uuid
      and d.storage_path = name
  )
);

-- Atomic authenticated document submission. This keeps the document row and
-- ingestion job in one transaction under the caller's RLS context.
create or replace function public.submit_document_with_job(
  p_organization_id uuid,
  p_filename text,
  p_storage_path text,
  p_content_hash text,
  p_pipeline_version text
)
returns table(
  document_id uuid,
  ingestion_job_id uuid,
  deduplicated boolean,
  document_status text
)
language plpgsql
security invoker
set search_path = public
as $
declare
  v_document public.documents;
  v_job public.ingestion_jobs;
begin
  if auth.uid() is null then
    raise exception 'authenticated user required';
  end if;

  if not exists (
    select 1
    from public.organization_members om
    where om.organization_id = p_organization_id
      and om.user_id = (select auth.uid())
  ) then
    raise exception 'organization membership required';
  end if;

  select d.*
    into v_document
  from public.documents d
  where d.organization_id = p_organization_id
    and d.content_hash = p_content_hash
    and d.pipeline_version = p_pipeline_version
  limit 1;

  if v_document.id is not null then
    select j.*
      into v_job
    from public.ingestion_jobs j
    where j.organization_id = p_organization_id
      and j.document_id = v_document.id
      and j.content_hash = p_content_hash
      and j.pipeline_version = p_pipeline_version
    order by j.created_at desc
    limit 1;

    if v_job.id is null then
      raise exception 'document exists without ingestion job';
    end if;

    return query select v_document.id, v_job.id, true, v_document.status;
    return;
  end if;

  insert into public.documents (
    organization_id, owner_user_id, filename, storage_path,
    content_hash, pipeline_version
  )
  values (
    p_organization_id, (select auth.uid()), p_filename, p_storage_path,
    p_content_hash, p_pipeline_version
  )
  returning * into v_document;

  insert into public.ingestion_jobs (
    organization_id, document_id, pipeline_version, content_hash
  )
  values (
    p_organization_id, v_document.id, p_pipeline_version, p_content_hash
  )
  returning * into v_job;

  return query select v_document.id, v_job.id, false, v_document.status;
end;
$;

grant execute on function public.submit_document_with_job(uuid, text, text, text, text)
  to authenticated;

revoke execute on function public.submit_document_with_job(uuid, text, text, text, text)
  from anon;

-- Atomic worker claim. This is intentionally a trusted-worker operation:
-- the function locks one eligible row before updating its lease, preventing two
-- workers from claiming the same job. It is not exposed to ordinary users.
create or replace function public.claim_ingestion_job(
  p_organization_id uuid,
  p_lease_seconds integer default 300
)
returns public.ingestion_jobs
language plpgsql
security definer
set search_path = public
as $$
declare
  claimed public.ingestion_jobs;
begin
  if p_lease_seconds <= 0 then
    raise exception 'lease_seconds must be positive';
  end if;

  select ij.*
    into claimed
  from public.ingestion_jobs ij
  where ij.organization_id = p_organization_id
    and (
      ij.status = 'PENDING'
      or (ij.status = 'PROCESSING' and ij.lease_until <= now())
    )
  order by ij.created_at asc
  for update skip locked
  limit 1;

  if claimed.id is null then
    return null;
  end if;

  update public.ingestion_jobs
  set status = 'PROCESSING',
      attempt_count = claimed.attempt_count + 1,
      lease_until = now() + make_interval(secs => p_lease_seconds),
      last_error = null,
      updated_at = now()
  where id = claimed.id
  returning * into claimed;

  return claimed;
end;
$$;

revoke execute on function public.claim_ingestion_job(uuid, integer) from public;
revoke execute on function public.claim_ingestion_job(uuid, integer) from anon;
revoke execute on function public.claim_ingestion_job(uuid, integer) from authenticated;
grant execute on function public.claim_ingestion_job(uuid, integer) to service_role;

-- Invoker function: RLS on document_chunks/documents remains active for the
-- caller. No SECURITY DEFINER is used here.
create or replace function public.match_document_chunks(
  query_embedding extensions.vector(384),
  match_count integer default 10,
  p_organization_id uuid default null
)
returns table (
  id uuid,
  document_id uuid,
  chunk_id text,
  content text,
  page integer,
  section text,
  start_char integer,
  end_char integer,
  similarity double precision
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  select
    dc.id,
    dc.document_id,
    dc.chunk_id,
    dc.content,
    dc.page,
    dc.section,
    dc.start_char,
    dc.end_char,
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc
  join public.documents d on d.id = dc.document_id
  where dc.embedding is not null
    and (
      p_organization_id is null
      or d.organization_id = p_organization_id
    )
  order by dc.embedding <=> query_embedding asc
  limit least(greatest(coalesce(match_count, 10), 1), 200);
$$;

revoke execute on function public.match_document_chunks(extensions.vector(384), integer, uuid) from public;
revoke execute on function public.match_document_chunks(extensions.vector(384), integer) from anon;
grant execute on function public.match_document_chunks(extensions.vector(384), integer) to authenticated;
