# Enterprise RAG — Architecture

**Phase 1 architecture decision record**  
**Date:** 2026-10-01

## 1. Current local architecture

Query
  ↓
Dense retrieval + BM25
  ↓
RRF hybrid fusion
  ↓
Cross-encoder reranking
  ↓
Context assembly
  ↓
OpenRouter generation
  ↓
Citation mapping / verification
  ↓
Faithfulness verification
  ↓
Observability / evaluation

The implementation keeps retrieval, ranking, generation, citation verification, and evaluation as separate modules.

## 2. Phase 1 production topology decision

The current FastAPI application initializes SentenceTransformers, FAISS, BM25, and a CrossEncoder during application startup. Therefore the full inference path is not assumed to belong inside Vercel Functions.

Selected topology:

Browser
  ↓
Vercel — React/Vite frontend
  ↓ HTTPS + user JWT
Long-running API / inference service
  ├── retrieval orchestration
  ├── embedding inference
  ├── reranking
  └── generation orchestration
  ├── Supabase Auth
  ├── Supabase Postgres / pgvector
  └── Supabase Storage
  ↓
Long-running ingestion worker

Candidate API/inference hosts are Fly.io, Railway, Cloud Run, or an equivalent long-running container platform.

**Decision:** Vercel owns the web UI first. Heavy Python inference is moved to a long-running service unless the Phase 1 resource benchmark proves a Vercel-compatible deployment is practical.

## 3. Quantitative feasibility gate

Run:

    python scripts/phase1_feasibility.py

For cached-model measurements:

    python scripts/phase1_feasibility.py --load-models

For concurrency:

    python scripts/phase1_feasibility.py --load-models --concurrency 4

The benchmark records source/package footprint, Python/platform information, model initialization, inference duration, reranking duration, and optional concurrent-request behavior.

The benchmark must be run on the target deployment environment before production deployment. Local measurements are evidence, not Vercel guarantees.

## 4. Async ingestion decision

**Selected mechanism: Supabase Postgres-backed job table + long-running worker with row leasing.**

The worker owns PDF parsing, OCR fallback, chunking, embedding, dense-index updates, tenant-scoped lexical-index updates, and READY/FAILED transitions.

Upload
  ↓
Supabase Storage
  ↓
documents + ingestion_jobs
  ↓
Worker claims job with lease
  ↓
parse → OCR → chunk → embed → index
  ↓
READY / FAILED

Job states:
- PENDING
- PROCESSING
- READY
- FAILED

A lease expiry makes PROCESSING jobs eligible for retry.

Idempotency key:
document_id + content_hash + pipeline_version

The worker must never depend on an HTTP request remaining open.

## 5. Tenant-safe lexical retrieval decision

**Selected mechanism: per-tenant BM25 indexes.**

Rationale:
- preserves BM25 semantics used by the current retrieval system;
- prevents a global lexical index from mixing tenants;
- keeps Dense-vs-Hybrid benchmarking comparable;
- supports tenant-scoped rebuild and deletion.

Lifecycle:

tenant document changes
  ↓
tenant lexical corpus marked stale
  ↓
worker rebuilds tenant BM25 index
  ↓
index version activated atomically

The index must contain only chunks belonging to the tenant. Query execution receives an explicit tenant ID and never falls back to a global corpus.

Trade-off: very large tenants may eventually require sharding or a different lexical service. PostgreSQL full-text search remains a possible scale-oriented alternative, but it is not the selected Phase 1 production lexical strategy because it changes the lexical algorithm.

## 6. Supabase request-path security decision

User JWTs are passed through to Supabase-backed operations wherever RLS should enforce ownership.

Browser JWT
  ↓
API authentication
  ↓
tenant/user context
  ↓
Supabase request with user authorization context
  ↓
RLS

The Supabase service-role key is not part of the ordinary user query path.

It may be used only for explicitly trusted operations such as migrations/admin provisioning or isolated worker operations that require privileged writes.

Every service-role operation must still enforce tenant/document ownership in application code.

RLS tests must be performed independently through an actual user-authorized request path.

## 7. Configuration boundary

Runtime configuration is centralized in app/config/settings.py.

Environment-controlled values include:
- local index paths
- embedding model
- reranker model
- retrieval top-k values
- API host/port
- CORS origins
- environment
- application version

No local Windows/WSL absolute paths are required.

## 8. Later-phase constraints

Phase 3–6 must preserve:
1. tenant isolation before retrieval;
2. explicit retrieval stages;
3. versioned embedding/index configuration;
4. asynchronous ingestion;
5. citation traceability;
6. provider-independent generation;
7. stage-level observability.

The architecture should not be rewritten around a framework unless benchmark or operational evidence justifies it.
