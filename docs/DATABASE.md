# Enterprise RAG — Production Data Model

**Phase 3 design draft — not applied to Supabase**

This document defines the production persistence model that will replace the current local-only persistence while preserving the existing retrieval architecture.

## 1. Design principles

- Tenant isolation is enforced before retrieval.
- `documents` is the source-document identity; `document_chunks` is the retrieval unit.
- Content hashes provide document-level idempotency.
- Chunk IDs remain stable within a versioned chunking pipeline.
- Embedding/model configuration is versioned with each embedding.
- Retrieval and answer telemetry is persisted separately from source content.
- RLS is enabled on exposed user-data tables.
- Service-role access is restricted to trusted worker/admin operations.
- The production lexical strategy remains per-tenant BM25, outside the Postgres schema.
- pgvector uses the same embedding dimensionality and distance convention as the validated FAISS baseline.

## 2. Entity model

organizations → organization_members → documents → document_chunks
                         │                 └── ingestion_jobs
                         └── users

users → conversations → messages → answers → citations

answers → retrieval_runs

## 3. Core tables

### organizations

- `id uuid primary key`
- `name text`
- `created_at timestamptz`

### organization_members

- `organization_id uuid`
- `user_id uuid`
- `role text`
- `created_at timestamptz`
- unique `(organization_id, user_id)`

### documents

- `id uuid primary key`
- `organization_id uuid`
- `owner_user_id uuid`
- `filename text`
- `storage_path text`
- `content_hash text`
- `pipeline_version text`
- `status text`
- `page_count integer`
- `metadata jsonb`
- `created_at timestamptz`
- `updated_at timestamptz`

Recommended uniqueness boundary: `(organization_id, content_hash, pipeline_version)`.

This prevents identical content from being unnecessarily re-indexed while allowing a deliberate pipeline-version change to create a new processing artifact.

### document_chunks

- `id uuid primary key`
- `document_id uuid`
- `chunk_id text`
- `content text`
- `page integer`
- `section text`
- `start_char integer`
- `end_char integer`
- `chunker_version text`
- `embedding_model text`
- `embedding_dimension integer`
- `embedding vector(<dimension>)`
- `metadata jsonb`
- `created_at timestamptz`

Recommended uniqueness: `(document_id, chunk_id, chunker_version)`.

The exact pgvector dimension must be pinned after the production embedding model is selected and measured against the existing FAISS baseline.

### ingestion_jobs

- `id uuid primary key`
- `organization_id uuid`
- `document_id uuid`
- `status text`
- `pipeline_version text`
- `content_hash text`
- `attempt_count integer`
- `lease_until timestamptz`
- `last_error text`
- `created_at timestamptz`
- `updated_at timestamptz`

Idempotency key: `document_id + content_hash + pipeline_version`.

Worker lifecycle: PENDING → PROCESSING → READY, with FAILED as the terminal error state. Expired PROCESSING leases become eligible for retry.

### conversations

- `id uuid primary key`
- `organization_id uuid`
- `user_id uuid`
- `title text`
- `created_at timestamptz`
- `updated_at timestamptz`

### messages

- `id uuid primary key`
- `conversation_id uuid`
- `user_id uuid`
- `role text`
- `content text`
- `created_at timestamptz`

### answers

- `id uuid primary key`
- `message_id uuid`
- `query_text text`
- `rewritten_query text nullable`
- `answer_text text`
- `retrieval_mode text`
- `faithfulness_status text nullable`
- `created_at timestamptz`

### citations

- `id uuid primary key`
- `answer_id uuid`
- `document_chunk_id uuid`
- `citation_label text`
- `valid boolean`
- `created_at timestamptz`

### retrieval_runs

- `id uuid primary key`
- `answer_id uuid`
- `organization_id uuid`
- `query_text text`
- `retrieval_mode text`
- `dense_count integer`
- `bm25_count integer`
- `fused_count integer`
- `reranked_count integer`
- `retrieval_latency_ms numeric`
- `rerank_latency_ms numeric`
- `generation_latency_ms numeric`
- `verification_latency_ms numeric`
- `total_latency_ms numeric`
- `input_tokens integer nullable`
- `output_tokens integer nullable`
- `estimated_cost numeric nullable`
- `created_at timestamptz`

## 4. pgvector parity gate

Before replacing the local dense index:

1. Freeze the embedding model/version.
2. Freeze embedding dimensionality.
3. Freeze normalization behavior.
4. Pin the distance metric.
5. Build a small parity corpus.
6. Compare top-k results between FAISS and pgvector.
7. Investigate ranking differences before migration.
8. Record latency separately.

The production vector index type and parameters must be selected from actual corpus size and benchmark results rather than assumed in advance.

## 5. RLS boundary

RLS should be enabled on all exposed user-data tables.

Intended ownership chain:

`auth.uid()` → `organization_members` → `organization_id` → documents / conversations / retrieval data.

Policies must authorize the actual organization membership or ownership relationship. `TO authenticated` alone is insufficient.

The production API must test the complete user-authorized request path, not only service-role queries.

## 6. Storage

PDFs live in Supabase Storage; database rows hold metadata and the storage path.

Lifecycle: upload → document row → ingestion job → READY.

Deletion must be idempotent and must invalidate both dense and tenant-scoped BM25 representations.

## 7. Deliberately not implemented yet

This is a schema/design artifact only. It does not create or modify a Supabase project, apply production DDL, choose a live embedding dimension, claim pgvector parity, implement RLS policies, implement Storage policies, or migrate local data.

Those steps require the actual Enterprise RAG Supabase project to be identified and the Phase 2 benchmark to be frozen before production retrieval migration.
