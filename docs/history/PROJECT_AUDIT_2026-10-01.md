# Enterprise RAG — Project Audit & Pause Point

**Audit date:** 2026-10-01  
**Purpose:** Complete project-state audit before pausing development and resuming tomorrow.  
**Repository:** Eklakh-AI-Engineer/ENTERPRISE-RAG  
**Default branch:** `main`  
**Audited HEAD:** `f98784e10bed49b103f059ec4188da6748a454e1`  
**Status:** PAUSED AFTER AUDIT

> This document is the authoritative pause-point snapshot for the work completed through 2026-10-01. The older `docs/IMPLEMENTATION_PLAN.md` is a living plan and contains some stale status entries from before the live Supabase work. Reconcile it against this audit when development resumes.

---

## 1. Executive Summary

Enterprise RAG has moved well beyond a basic RAG demo.

The project currently contains a substantial retrieval-engineering core plus a production-oriented persistence, tenant-isolation, authentication, Supabase, ingestion, evaluation, and observability foundation.

### Current reality

- **Core retrieval engine:** substantially implemented.
- **Evaluation framework:** substantially implemented, but the benchmark is not yet scientifically complete.
- **Production database:** dedicated Supabase project created and schema applied.
- **pgvector:** live and tenant-scoped retrieval function deployed.
- **Authentication:** application boundary exists and `/auth/me` is wired.
- **Multi-tenancy:** design and RLS foundation exist, but real two-user end-to-end isolation has **not** been demonstrated yet.
- **Production ingestion:** domain services, worker orchestration, storage adapter, embedding/indexing pipeline, and worker composition exist; end-to-end live ingestion remains unfinished.
- **Production query path:** **not switched** to the Supabase/pgvector path yet.
- **BM25 production lifecycle:** not implemented.
- **CI:** configured, but the latest HEAD currently has no reported combined status from the GitHub status endpoint; do not claim green CI.
- **Production deployment:** not completed.
- **Phase 2 benchmark:** still blocked by final human relevance labels / experiment execution.

### Bottom line

**This is a strong engineering foundation, not a finished production product.**

The correct next milestone is to prove the live path end-to-end without weakening tenant isolation:

`authenticated user → organization → document → storage → ingestion job → worker → chunks → embeddings → pgvector → tenant-scoped retrieval → query`

---

# 2. What Is DONE

## 2.1 Core RAG / Retrieval Engine

### Retrieval

- [x] Dense retrieval
- [x] SentenceTransformers embedding pipeline
- [x] FAISS dense index
- [x] BM25 lexical retrieval
- [x] Hybrid retrieval
- [x] RRF fusion
- [x] Cross-encoder reranking
- [x] Candidate generation and ranking separation
- [x] Context assembly

### Generation

- [x] OpenRouter generation adapter
- [x] RAG generation pipeline
- [x] Evidence-grounded generation architecture

### Citations / Evidence

- [x] Citation mapping
- [x] Citation verification
- [x] Claim-level verification infrastructure
- [x] Evidence traceability
- [x] Faithfulness verification architecture

### Observability

- [x] Stage-level latency instrumentation
- [x] Retrieval/reranking/generation/verification telemetry concepts
- [x] Retrieval run persistence model
- [x] Pipeline observability UI/development evidence

---

# 3. Parsing / Chunking

## PDF processing

- [x] PyMuPDF native extraction
- [x] Page-level provenance
- [x] OCR fallback implementation using Tesseract
- [x] Parser versioning
- [x] Extraction-method metadata

### Important nuance

OCR is implemented in the parser, but **full production OCR validation across representative scanned-document workloads is still pending**.

## Chunking

- [x] Recursive chunking
- [x] Stable chunk IDs
- [x] Page metadata
- [x] Section metadata
- [x] Character spans
- [x] Chunker versioning
- [x] Durable page/span evidence mapping

- [ ] Semantic chunking

Semantic chunking remains deliberately unimplemented.

---

# 4. Evaluation — Phase 2

## Harness DONE

- [x] Phase 2 benchmark schema
- [x] Benchmark validation
- [x] 50–100 query contract
- [x] 10+ category contract
- [x] Durable document/page/span evidence labels
- [x] Recall@5 / Recall@10
- [x] MRR
- [x] Graded nDCG@5 / nDCG@10
- [x] Bootstrap confidence intervals
- [x] Paired bootstrap delta confidence intervals
- [x] Dense-vs-Hybrid experiment harness
- [x] Faithfulness judge metadata
- [x] Human faithfulness-validation schema
- [x] Faithfulness evaluation script

## CHA corpus

Frozen corpus:

- Business Expense
- Employee Handbook 2025
- Information Security
- Procurement

Corpus version:

`v1.1`

Corpus hash:

`c85eaf4bd9a958f1864f4c030be5ea04f69faf20a3c011cf50239b67cf1fccc0`

Frozen candidate pool:

- 50 queries
- 780 candidates
- Dense ∪ BM25 pooling
- source/rank/score provenance preserved

## Evaluation still PENDING

- [ ] Final relevance judgments
- [ ] Human labeling of pooled candidates
- [ ] Freeze benchmark configuration hash
- [ ] Dense-vs-Hybrid experiment execution
- [ ] Query-level failure analysis
- [ ] Retrieval case studies
- [ ] Human validation of faithfulness judge
- [ ] Held-out answer evaluation
- [ ] Final benchmark report

### Silver-label status

OpenRouter paid-model attempts were blocked by account credit/quota constraints.

Free-model labeling was attempted, but the workflow exhausted available free-model rate limits before producing labels.

Current silver-label artifact is therefore a **rate-limited checkpoint**, not a completed dataset.

Do not describe the Phase 2 benchmark as completed.

---

# 5. Reproducibility / Repository Engineering

## DONE

- [x] Bounded `requirements.txt`
- [x] Dockerfile
- [x] `.dockerignore`
- [x] `.env.example`
- [x] Centralized configuration
- [x] Pytest configuration
- [x] GitHub Actions CI workflow
- [x] Development documentation
- [x] Architecture documentation
- [x] Deployment documentation
- [x] Security documentation
- [x] Evaluation documentation
- [x] Database design documentation

## Still pending

- [ ] Clean-checkout installation verification
- [ ] Clean startup verification
- [ ] Frontend clean build verification
- [ ] Target-runtime ML resource benchmark
- [ ] First fully verified green CI result on the current HEAD

### CI caution

The latest HEAD currently has no combined status entries reported by the GitHub status endpoint.

Therefore:

**CI is configured, but CI should not be described as passing.**

---

# 6. Production Supabase Infrastructure

A major milestone was completed today.

## Dedicated project

A dedicated **Enterprise-RAG** Supabase project was created in `ap-south-1`.

The unrelated `Tackboard` project was not modified.

## Live database

The Enterprise RAG project has:

- [x] PostgreSQL
- [x] pgvector
- [x] organizations
- [x] organization_members
- [x] documents
- [x] document_chunks
- [x] ingestion_jobs
- [x] conversations
- [x] messages
- [x] answers
- [x] citations
- [x] retrieval_runs
- [x] RLS policies
- [x] private documents Storage bucket
- [x] Storage policies
- [x] atomic ingestion-job claim RPC
- [x] tenant-scoped pgvector retrieval RPC

Live verification performed during the session established:

- 10 expected core tables
- 17 public-table RLS policies
- 3 Storage policies
- private `documents` bucket
- worker claim function
- tenant-scoped vector-search function
- vector search function is `SECURITY INVOKER`

## Important security fix

The initial unscoped vector-search overload was removed from the live database.

There is now only the tenant-aware function:

`match_document_chunks(vector, integer, uuid)`

The third argument is the organization scope.

This prevents accidentally falling back to an unscoped vector-search API.

---

# 7. Persistence Layer

## DONE

Application persistence contracts:

- [x] Document entity
- [x] Ingestion job entity
- [x] Conversation entity
- [x] Message entity
- [x] Answer entity
- [x] Citation entity
- [x] Retrieval telemetry entity

Repository interfaces:

- [x] DocumentRepository
- [x] IngestionJobRepository
- [x] WorkerJobRepository
- [x] ConversationRepository
- [x] AnswerRepository
- [x] ChunkRepository

Adapters:

- [x] In-memory repositories
- [x] Supabase document repository
- [x] Supabase ingestion repository
- [x] Supabase conversation repository
- [x] Supabase answer/citation/retrieval adapters
- [x] Supabase chunk persistence adapter

## Document lifecycle

Implemented:

- [x] SHA-256 content hashing
- [x] Tenant-scoped deduplication
- [x] Pipeline-version-aware identity
- [x] Deterministic Storage paths
- [x] Ingestion-job creation
- [x] Idempotent duplicate submission behavior

---

# 8. Storage

## DONE

- [x] DocumentStorage protocol
- [x] In-memory Storage implementation
- [x] Supabase Storage adapter
- [x] Private bucket design
- [x] Tenant-scoped path design
- [x] Storage contract tests
- [x] Live private bucket/policies

## Pending

- [ ] Real authenticated upload through the final API contract
- [ ] Live upload/download integration test
- [ ] Deletion lifecycle
- [ ] Document deletion → chunk invalidation
- [ ] Document deletion → BM25 invalidation
- [ ] Retention policy

---

# 9. Authentication / Authorization

## DONE

Authentication foundation:

- [x] AuthenticatedPrincipal
- [x] TokenVerifier protocol
- [x] Supabase verified-claims adapter
- [x] Bearer-token parsing
- [x] Invalid-token handling
- [x] Role validation
- [x] `/auth/me` endpoint
- [x] Authentication unit tests
- [x] Supabase integration boundary

The application deliberately does not manually decode JWTs.

## NOT DONE

- [ ] Real Supabase Auth users
- [ ] Organization bootstrap flow
- [ ] Membership management API
- [ ] User A/User B isolation test
- [ ] Full request-path RLS verification
- [ ] Production authorization middleware for every protected resource
- [ ] OAuth/magic-link product flow
- [ ] Password-reset/product auth UX

### Current live Auth state

The dedicated Supabase project currently has **no Auth users**.

Therefore actual two-user authorization/RLS testing has not yet been performed.

---

# 10. Tenant Isolation

## Design DONE

The intended security model is:

`auth.uid()`

→ organization membership

→ organization ID

→ documents/chunks/conversations/retrieval data

### Explicit design decisions

- [x] Tenant isolation before retrieval
- [x] Tenant-scoped pgvector retrieval
- [x] Per-tenant BM25 strategy selected
- [x] Global BM25 + post-filtering rejected
- [x] Private document Storage
- [x] Organization-scoped persistence contracts
- [x] Service-role use restricted to trusted operations

## Verification PENDING

- [ ] User A cannot retrieve User B documents
- [ ] User A cannot retrieve User B chunks
- [ ] User A cannot download User B PDFs
- [ ] User A cannot access User B conversations
- [ ] User A cannot forge organization IDs
- [ ] RLS tested through actual authenticated client
- [ ] Service-role worker authorization tested independently

**This is one of the most important remaining security gates.**

---

# 11. Ingestion Worker

## DONE

Worker lifecycle:

`PENDING → PROCESSING → READY`

with:

`FAILED`

as an error state.

Implemented:

- [x] Atomic job claim contract
- [x] Lease duration
- [x] Attempt count
- [x] Lease expiry
- [x] Retry semantics
- [x] PDF ingestion pipeline
- [x] OCR fallback
- [x] Recursive chunking
- [x] Embedding provider
- [x] Durable chunk persistence
- [x] Worker orchestration
- [x] Production worker dependency factory
- [x] Worker tests

## Still pending

- [ ] Actual live worker execution against the Enterprise RAG project
- [ ] Background worker deployment
- [ ] Retry/backoff policy beyond lease retry
- [ ] Worker heartbeat/lease extension for long documents
- [ ] Dead-letter strategy
- [ ] Concurrent-worker integration testing
- [ ] Idempotent replacement of stale chunks on re-ingestion
- [ ] Tenant BM25 rebuild inside worker
- [ ] Operational monitoring

### Important indexing caveat

Current durable chunk persistence is an **upsert**, not a fully transactional replace.

If a document is re-ingested and produces fewer/different chunks, stale chunks can remain.

Before calling production indexing complete, implement one of:

- transactional delete+insert;
- versioned document chunks;
- atomic DB replacement RPC.

---

# 12. Embeddings / pgvector

## DONE

- [x] EmbeddingProvider abstraction
- [x] SentenceTransformers provider
- [x] `all-MiniLM-L6-v2`
- [x] 384 dimensions
- [x] normalized embeddings
- [x] embedding count validation
- [x] pgvector persistence adapter
- [x] tenant-scoped pgvector search adapter
- [x] live tenant-scoped RPC
- [x] HNSW reference index

## PENDING

- [ ] Live production embedding ingestion
- [ ] FAISS-vs-pgvector parity benchmark
- [ ] Latency benchmark
- [ ] Filtered-search benchmark
- [ ] Production index parameter tuning
- [ ] Embedding model freeze for production
- [ ] Re-indexing/version migration strategy

---

# 13. BM25 Production Strategy

Architecture decision:

**Per-tenant BM25 indexes.**

This is intentionally different from global BM25 + post-filtering.

## DONE

- [x] Tenant-safe strategy selected
- [x] Lifecycle requirements documented
- [x] Refresh/rebuild concept documented
- [x] Deletion/invalidation requirement documented

## PENDING

- [ ] Durable tenant BM25 corpus
- [ ] Tenant index creation
- [ ] Tenant index refresh
- [ ] Tenant index rebuild
- [ ] Tenant index deletion
- [ ] Version activation
- [ ] Worker integration
- [ ] Production benchmark

---

# 14. Query / Conversation Layer

## DONE

- [x] Conversation entities
- [x] Message entities
- [x] Answer persistence
- [x] Citation persistence
- [x] Retrieval telemetry persistence
- [x] Conversation service
- [x] Answer persistence service
- [x] Supabase adapters

## NOT DONE

- [ ] Production tenant-aware query endpoint
- [ ] Query → pgvector
- [ ] Query → tenant BM25
- [ ] Query → hybrid RRF
- [ ] Query → reranking
- [ ] Query → generation
- [ ] Query → citations
- [ ] Query → faithfulness
- [ ] Query → persisted answer/retrieval telemetry
- [ ] Conversation history in production query path

### Critical fact

The current `/query` endpoint still uses the existing local `QueryPipeline`.

It has **not** been switched to the production Supabase/pgvector path.

That is intentional.

---

# 15. Query Rewriting

- [ ] Query rewriting
- [ ] Query expansion
- [ ] Query decomposition
- [ ] Rewrite evaluation
- [ ] Rewrite latency/cost instrumentation

This remains a later retrieval-quality feature.

---

# 16. Production Deployment

## Architecture selected

`React/Vite frontend`

→ Vercel

`Python FastAPI inference service`

→ long-running container platform

`Supabase`

→ Auth + Postgres + pgvector + Storage

`Long-running worker`

→ ingestion/indexing

## DONE

- [x] Deployment topology decision
- [x] Docker path
- [x] Environment configuration
- [x] Architecture documentation

## PENDING

- [ ] Target runtime benchmark
- [ ] Backend hosting selection
- [ ] Backend deployment
- [ ] Worker deployment
- [ ] Vercel deployment
- [ ] Production CORS configuration
- [ ] Domain configuration
- [ ] HTTPS verification
- [ ] Production secrets
- [ ] Health checks
- [ ] Logs
- [ ] Monitoring
- [ ] Alerts

---

# 17. Security / Hardening

## DONE

- [x] Environment-based secrets
- [x] No frontend provider-secret design
- [x] Private Storage bucket
- [x] Tenant-scoped vector search
- [x] RLS design
- [x] Service-role boundary
- [x] JWT verification boundary
- [x] Upload filename validation in domain service
- [x] Content hashing

## PENDING

- [ ] Rate limiting
- [ ] Quotas
- [ ] Abuse controls
- [ ] Request-size enforcement at deployment layer
- [ ] Production upload endpoint hardening
- [ ] Prompt-injection corpus
- [ ] Adversarial document tests
- [ ] Secret-safe logging audit
- [ ] Dependency vulnerability scan
- [ ] Security headers
- [ ] Production CORS lockdown
- [ ] Audit logging

---

# 18. Frontend

## Existing

- [x] React/Vite frontend
- [x] Working development UI
- [x] Retrieval/evidence inspection UI
- [x] Observability/evaluation presentation

## Production work remaining

- [ ] Authentication UI
- [ ] Organization/workspace selection
- [ ] Document upload
- [ ] Upload status
- [ ] Ingestion progress
- [ ] Document management
- [ ] Tenant-scoped conversations
- [ ] Production query UX
- [ ] Citation interaction
- [ ] Error/loading states
- [ ] Mobile/browser QA
- [ ] Production deployment

---

# 19. Important Things NOT to Claim Yet

Until the corresponding gates are completed, do **not** describe the project as:

- production-ready;
- fully multi-tenant;
- fully RLS-verified;
- benchmark-proven;
- Hybrid retrieval experimentally proven superior;
- pgvector parity-proven;
- fully asynchronous in production;
- production-deployed;
- end-to-end authenticated;
- fully cost-observed;
- fully secure against prompt injection.

The architecture supports these goals, but verification is still required.

---

# 20. Current Repository / Implementation State

### Current HEAD

`f98784e10bed49b103f059ec4188da6748a454e1`

Latest commit:

`docs: record production ingestion composition progress`

### Recent important milestones

- Phase 0 baseline freeze
- Phase 1 reproducibility/architecture hardening
- Phase 2 evaluation harness
- CHA corpus freeze
- Silver-label workflow/checkpoint
- Production persistence abstractions
- Supabase reference schema
- Dedicated Enterprise RAG Supabase project
- Live database migration
- Storage policies
- Authentication boundary
- Tenant-scoped pgvector retrieval
- Production ingestion worker composition

---

# 21. Recommended Resume Order

When development resumes, **do not randomly pick another feature**.

Follow this order.

## Step 1 — Create real Auth users

- [ ] Create test User A
- [ ] Create test User B
- [ ] Create Organization A
- [ ] Create Organization B
- [ ] Add memberships

## Step 2 — Verify RLS

- [ ] User A → A documents = allowed
- [ ] User A → B documents = denied
- [ ] User A → B Storage = denied
- [ ] User A → B retrieval = denied
- [ ] User A → B conversations = denied

## Step 3 — Finish live ingestion

- [ ] Authenticated document upload
- [ ] Storage upload
- [ ] Job creation
- [ ] Worker claim
- [ ] PDF/OCR
- [ ] Chunking
- [ ] Embedding
- [ ] pgvector persistence
- [ ] READY transition

## Step 4 — Fix indexing idempotency

Implement atomic replacement/versioning so stale chunks cannot survive re-ingestion.

## Step 5 — pgvector parity

Run:

`FAISS top-k` vs `pgvector top-k`

and record:

- overlap;
- ranking differences;
- latency;
- filtered-search behavior.

## Step 6 — Production BM25

Implement per-tenant BM25 lifecycle.

## Step 7 — Production QueryPipeline

Only after Steps 1–6:

`JWT → tenant → pgvector + BM25 → RRF → reranker → generation → citations → faithfulness → persistence`

## Step 8 — Complete Phase 2

- final labels;
- Dense-vs-Hybrid experiment;
- failure analysis;
- faithfulness human validation;
- answer evaluation.

## Step 9 — Deployment/security

- backend;
- worker;
- frontend;
- secrets;
- CORS;
- monitoring;
- rate limits;
- security QA.

---

# 22. Tomorrow's Exact Starting Point

**Resume from here:**

### `LIVE MULTI-TENANT INTEGRATION`

First task:

> Create two test Auth users and perform real RLS/Storage/tenant-isolation tests against the dedicated Enterprise RAG Supabase project.

Then:

> Complete live PDF ingestion from authenticated upload through pgvector.

Then:

> Run FAISS-vs-pgvector parity.

Do **not** switch `/query` to production retrieval before those checks pass.

---

# 23. Pause-Point Definition

At the moment this audit was written:

```
CORE RAG                         ████████████████████  DONE
EVALUATION ENGINE               █████████████████░░░  MOSTLY DONE
EVALUATION DATA                 ███████████░░░░░░░░░  INCOMPLETE
DATABASE                         ████████████████████  LIVE
AUTH FOUNDATION                 ███████████████░░░░░  PARTIAL
TENANT ISOLATION                █████████████░░░░░░░  DESIGN + RPC
INGESTION                       █████████████░░░░░░░  FOUNDATION
PGVECTOR                        ███████████████░░░░░  FOUNDATION + LIVE RPC
BM25 PRODUCTION                 █████░░░░░░░░░░░░░░░  DESIGN ONLY
PRODUCTION QUERY                █████░░░░░░░░░░░░░░░  NOT WIRED
DEPLOYMENT                      ███░░░░░░░░░░░░░░░░░  NOT DONE
SECURITY QA                     ███████░░░░░░░░░░░░░  INCOMPLETE
PRODUCT RELEASE                 ████░░░░░░░░░░░░░░░░  NOT DONE
```

**Pause here.**

The project has a solid foundation and a clear continuation path. The next session should focus on **verification of the live security/data path**, not adding another abstraction layer.

---

## Final status

**Enterprise RAG is currently in the transition from retrieval-engineering prototype → production multi-tenant system.**

The difficult architectural decisions are largely made.

The remaining work is increasingly about **integration, verification, benchmarking, operational hardening, and deployment** rather than inventing the core architecture.
