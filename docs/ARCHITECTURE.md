# Enterprise RAG — Architecture

**Current architecture direction:** local-first retrieval engineering  
**Date:** 2026-10-03

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

## 2. Later production topology

Production is intentionally deferred until the local retrieval benchmark and product are frozen.

Target topology:

Browser
  ↓
Vercel — React/Vite frontend
  ↓ HTTPS + authenticated user context
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

The production host is not fixed yet. The deployment choice will be made after a target-runtime feasibility measurement.

## 3. Production feasibility gate

Before production deployment, measure the actual target runtime for:

- Python/package footprint;
- model initialization;
- embedding inference;
- reranking;
- concurrent-request behavior;
- memory and startup characteristics.

Local measurements are evidence for development, not guarantees about a target hosting platform.

## 4. Async ingestion target

The intended production mechanism is a Supabase Postgres-backed job table plus a long-running worker with row leasing.

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

The worker must support multi-tenant job claiming, lease recovery, idempotency,
and tenant-safe index updates before production release.

## 5. Tenant-safe lexical retrieval target

The intended production lexical strategy is per-tenant BM25 indexes.

The index must contain only chunks belonging to the tenant. Query execution
receives an explicit tenant ID and never falls back to a global corpus.

## 6. Supabase request-path security target

User JWTs are passed through to Supabase-backed operations wherever RLS should
enforce ownership.

The Supabase service-role key is not part of the ordinary user query path. It is
reserved for explicitly trusted operations such as migrations/admin provisioning
or isolated worker operations.

RLS tests must be performed independently through an actual user-authorized
request path.

## 7. Configuration boundary

Runtime configuration is centralized in app/config/settings.py.

Environment-controlled values include:

- local index paths;
- embedding model;
- reranker model;
- retrieval top-k values;
- API host/port;
- CORS origins;
- environment;
- application version.

No local Windows/WSL absolute paths are required.

## 8. Architectural constraints

The system should preserve:

1. tenant isolation before retrieval;
2. explicit retrieval stages;
3. versioned embedding/index configuration;
4. asynchronous ingestion;
5. citation traceability;
6. provider-independent generation;
7. stage-level observability.

The architecture should not be rewritten around a framework unless benchmark or
operational evidence justifies it.
