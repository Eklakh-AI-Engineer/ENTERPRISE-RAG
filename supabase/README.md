# Enterprise RAG — Supabase Artifacts

This directory contains database schema and migration artifacts for the Enterprise RAG persistence layer.

## Role in the repository

Supabase is a **later-stage production boundary**, while the current milestone remains local-first retrieval engineering.

The artifacts cover:

- organizations and memberships;
- documents and document chunks;
- ingestion jobs;
- conversations, messages, answers, and citations;
- retrieval telemetry;
- pgvector;
- RLS policies;
- private document Storage;
- trusted-worker ingestion claim semantics.

## Source of truth

- schema.sql — reviewed reference DDL.
- migrations/ — versioned migration history where applicable.
- ../docs/DATABASE.md — data-model and parity contract.

Do not treat narrative documentation as a replacement for versioned migrations.

## Security boundary

Normal user operations must use user authorization context so RLS can enforce tenant ownership.

Service-role credentials are restricted to trusted worker/admin operations. A service-role query is not evidence that RLS works.

The tenant-aware vector-search boundary is explicit; an unscoped vector-search fallback is not acceptable.

## Production gate

Before production release:

1. freeze the local retrieval benchmark;
2. verify FAISS-vs-pgvector ranking parity;
3. verify authenticated API request propagation;
4. run cross-tenant negative tests through the real application path;
5. verify Storage isolation;
6. verify ingestion idempotency and chunk replacement;
7. deploy only after the local product gates pass.

See [../docs/DATABASE.md](../docs/DATABASE.md), [../docs/SECURITY.md](../docs/SECURITY.md), and [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).
