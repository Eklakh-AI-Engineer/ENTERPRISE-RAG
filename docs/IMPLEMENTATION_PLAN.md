# Enterprise RAG — End-to-End Implementation Plan

> Living implementation plan for taking Enterprise RAG from the current retrieval-engineering baseline to a production-ready Vercel + Supabase product.

**Last updated:** 2026-10-01  
**Architecture decision gate:** Phase 1 must resolve Vercel inference feasibility, async worker placement, BM25 tenant isolation, and Supabase auth/RLS request-path strategy before Phases 3–6 begin.  
**Current phase:** Phase 2 empirical benchmark in progress → Phase 3 production data layer preparation in parallel  
**Baseline commit:** `f91ecff3a1a2d430e83ba2fafa3b40d72b2f3a8f`  
**Phase 0 freeze commit:** `298a8e5aa886793d56a18dc0426a8952c681f1d6`

---

## 1. Status Legend

- [x] **COMPLETE** — implemented and verified enough to count as done.
- [~] **PARTIAL / INCOMPLETE** — meaningful implementation exists, but required scope is not complete.
- [ ] **PENDING** — not implemented yet.
- **Gate** — work that must be completed before the next production stage.

---

# 2. Current State

## Overall assessment

The core RAG/retrieval engine is substantially implemented. The remaining work is concentrated in:

1. reproducibility and repository hygiene,
2. rigorous retrieval evaluation,
3. production persistence,
4. ingestion reliability,
5. authentication and tenant isolation,
6. production query/conversation architecture,
7. deployment/security/observability,
8. final product QA.

The project should **not** be treated as production-ready yet.

### Current maturity

| Area | Status | State |
|---|---|---|
| Retrieval architecture | [x] | Core engine implemented |
| Dense retrieval | [x] | SentenceTransformers + FAISS |
| BM25 | [x] | Lexical retrieval implemented |
| Hybrid retrieval | [x] | RRF-based fusion implemented |
| Cross-encoder reranking | [x] | Implemented |
| Citation mapping | [x] | Implemented |
| Citation validation | [x] | Implemented |
| Faithfulness verification | [x] | Implemented |
| Pipeline metrics | [x] | Stage-level latency/quality metrics |
| FastAPI API | [x] | Working development API |
| React/Vite UI | [x] | Working inspection/demo UI |
| Evaluation metrics | [x] | Recall/MRR/nDCG + bootstrap infrastructure implemented |
| Evaluation dataset | [~] | 50-query CHA pool frozen; final relevance labels still pending |
| Dense vs Hybrid experiment | [ ] | Not completed |
| Failure analysis | [ ] | Not completed systematically |
| Query rewriting | [ ] | Not implemented |
| OCR fallback | [ ] | Not complete |
| Semantic chunking | [ ] | Not implemented |
| Token/cost accounting | [~] | Partial observability; systematic accounting required |
| Reproducible dependencies | [x] | Bounded requirements, Docker, env template implemented |
| Production database | [~] | Phase 3 reference schema implemented; live project not selected |
| Supabase/pgvector | [~] | Reference DDL and similarity contract implemented; live verification pending |
| Supabase Storage | [ ] | Not implemented |
| Authentication | [ ] | Not implemented |
| RLS / tenant isolation | [ ] | Not implemented |
| Persistent conversations | [ ] | Not implemented |
| Async ingestion | [ ] | Not implemented |
| Production deployment | [ ] | Not implemented |
| CI/CD | [~] | Minimal GitHub Actions CI implemented; first full green verification remains |
| Production security | [ ] | Not complete |
| Production browser QA | [ ] | Not complete |

---

# 3. Phase 0 — Baseline Freeze

**Status: [x] COMPLETE**

### Completed

- [x] Identified the current working baseline.
- [x] Preserved the existing retrieval/generation behavior.
- [x] Documented the frozen pipeline.
- [x] Documented implemented capabilities.
- [x] Documented known limitations.
- [x] Added `docs/PHASE_0_BASELINE.md`.
- [x] Committed the freeze as `298a8e5aa886793d56a18dc0426a8952c681f1d6`.

### Exit condition

**Complete.**

No Phase 0 functional work remains.

---

# 4. Phase 1 — Repository Cleanup + Reproducibility

**Status: [~] IMPLEMENTED — ARCHITECTURE SPIKES COMPLETE; TARGET-RUNTIME RESOURCE MEASUREMENT REMAINS**

## Objective

Make the existing system deterministic, installable, understandable, and safe to modify before production migration.

### 1.1 Repository hygiene

- [x] Removed accidental root version/artifact files.
- [x] Removed obsolete root Node artifacts; the active frontend keeps its own package manifest/lockfile.
- [x] Hardened root .gitignore for environments, caches, generated indexes, model artifacts, and frontend build output.
- [x] Preserved tracked evaluation/documentation material.

### 1.2 Dependency reproducibility

- [x] Populated requirements.txt with runtime and development dependencies.
- [x] Added bounded version constraints for reproducibility.
- [x] Added Dockerfile with a pinned Python 3.12 runtime line.
- [x] Added .dockerignore.
- [x] Added .env.example.
- [ ] Full clean-checkout installation has not been executed in this tool environment because external package installation is unavailable.
- [x] Frontend retains its checked-in package-lock.json.
- [x] No real secrets are committed by the Phase 1 changes.

### 1.3 Configuration

- [x] Centralized runtime configuration in app/config/settings.py.
- [x] API CORS is environment-driven.
- [x] Retrieval top-k/candidate settings are environment-driven.
- [x] Model names are environment-driven.
- [x] Frontend API endpoint is environment-driven through VITE_API_BASE_URL.
- [x] No Windows/WSL absolute path is required.

### 1.4 Minimal CI protection

- [x] Added GitHub Actions for push to main and pull requests.
- [x] Backend job installs requirements, compiles Python, and runs pytest.
- [x] Frontend job runs npm ci, lint, and production build.
- [ ] First workflow execution still needs to complete successfully on GitHub.

### 1.5 Vercel / inference feasibility spike — **MUST COMPLETE BEFORE PRODUCTION DEPLOYMENT**

- [x] Added scripts/phase1_feasibility.py.
- [x] Benchmark records Python/platform, repository footprint, installed package footprint, model initialization, inference, reranking, and optional concurrency.
- [x] Documented the split topology decision: Vercel frontend + long-running Python inference unless target-runtime measurements prove otherwise.
- [ ] Execute the benchmark on the target runtime.
- [ ] Record target-runtime bundle/package size, cold start, peak memory, execution duration, and concurrency results in docs/DEPLOYMENT.md.

**Preliminary topology decision:** keep heavy ML inference off Vercel Functions by default because SentenceTransformers and CrossEncoder are initialized at application startup. This is an architecture decision, not a claim that Vercel is impossible.

### 1.6 Async ingestion architecture spike — **DECIDED IN PHASE 1**

- [x] Selected a Supabase Postgres-backed ingestion_jobs table with worker row leasing.
- [x] Defined ownership of parsing, OCR, chunking, embedding, dense indexing, and lexical indexing.
- [x] Defined PENDING → PROCESSING → READY / FAILED states.
- [x] Defined lease expiry/retry semantics.
- [x] Defined idempotency key: document_id + content_hash + pipeline_version.
- [x] Documented the decision in docs/ARCHITECTURE.md.

### 1.7 Tenant-safe BM25 + RLS architecture decision — **DECIDED IN PHASE 1**

- [x] Selected per-tenant BM25 indexes.
- [x] Defined tenant-scoped index lifecycle, refresh, rebuild, and deletion requirements.
- [x] Explicitly rejected global BM25 plus post-filtering.
- [x] Documented benchmark comparability and scale trade-offs.
- [x] Documented the decision in docs/ARCHITECTURE.md.

### 1.8 Supabase request-path security decision — **DECIDED IN PHASE 1**

- [x] Selected user JWT propagation for ordinary Supabase-backed operations.
- [x] Restricted service-role usage to explicitly trusted operations.
- [x] Documented that service-role access is not evidence that RLS works.
- [x] Defined actual API-path and cross-tenant negative testing requirements.
- [x] Documented the decision in docs/ARCHITECTURE.md and docs/SECURITY.md.

### 1.9 Documentation

- [x] Updated README installation/deployment guidance.
- [x] Added docs/ARCHITECTURE.md.
- [x] Added docs/EVALUATION.md.
- [x] Added docs/DEVELOPMENT.md.
- [x] Added docs/DEPLOYMENT.md.
- [x] Added docs/SECURITY.md.
- [x] Documented local backend/frontend startup.
- [x] Documented test commands.
- [x] Documented environment variables.

### Phase 1 gate

Implemented:

- [x] Repository cleanup.
- [x] Reproducible dependency specification.
- [x] Docker reproducibility path.
- [x] Environment/configuration templates.
- [x] Minimal CI.
- [x] Architecture decisions for Vercel/inference, async ingestion, tenant-safe BM25, and Supabase JWT/RLS.

Still required before declaring the Phase 1 gate fully closed:

- [ ] First GitHub Actions run passes.
- [ ] Clean-checkout backend installation/startup is verified.
- [ ] Frontend clean-checkout build is verified.
- [ ] Target-runtime inference/resource benchmark is executed and recorded.

**Phase 2 must not start production retrieval migration until the remaining gate items are closed.**

# 5. Phase 2 — Evaluation Completion + Retrieval Experiment

**Status: 🟡 IMPLEMENTED HARNESS + PROTOCOL; LABELED DATASET AND EXPERIMENT RUN REMAIN**

## Objective

Turn the existing retrieval implementation into a reproducible, statistically defensible retrieval evaluation.

### 2.1 Benchmark freeze

- [x] Added a versioned Phase 2 benchmark schema.
- [x] Added a benchmark example/template.
- [x] Defined 50–100 labeled queries as the acceptance range.
- [x] Defined durable document/page/span evidence labels.
- [x] Added page character offsets and chunker version metadata to recursive chunks.
- [x] Defined benchmark versioning and reproducibility metadata.
- [x] Populate the 50-query CHA candidate pool from the frozen corpus.
- [x] Freeze and record the CHA corpus snapshot hash.
- [ ] Freeze the final relevance judgments and benchmark configuration hash.

### 2.2 Unbiased relevance pooling

- [x] Added scripts/build_relevance_pool.py.
- [x] Pooling rule is Dense(query) ∪ BM25(query).
- [x] Pool artifact preserves document/page/section/text and retrieval source/rank.
- [x] Run pooling against the frozen CHA corpus.
- [ ] Human-judge the pooled candidates.
- [ ] Freeze the resulting relevance judgments.

### 2.3 Retrieval metrics

- [x] Recall@5 and Recall@10.
- [x] MRR.
- [x] Graded nDCG@5 and nDCG@10.
- [x] Bootstrap confidence intervals.
- [x] Paired bootstrap treatment-minus-baseline confidence intervals.
- [x] Added automated tests for nDCG/bootstrap behavior.

### 2.4 Controlled Dense-vs-Hybrid experiment

- [x] Added scripts/run_dense_vs_hybrid.py.
- [x] Dense is the baseline.
- [x] Dense + BM25 + RRF is the treatment.
- [x] Same corpus, queries, judgments, and evaluation code.
- [x] Reranker excluded from this experiment to isolate retrieval strategy.
- [x] Query-level paired deltas are recorded.
- [x] Aggregate and category-level results are recorded.
- [ ] Run the experiment on the frozen benchmark after final human relevance labels are available.
- [ ] Publish the resulting raw JSON artifact and analysis.
- [ ] Perform failure analysis before making a retrieval-quality claim.

### 2.5 Faithfulness judge validation

- [x] Faithfulness output now records judge model, prompt version, and temperature.
- [x] Faithfulness judge temperature is explicitly set.
- [x] Added human-validation subset schema/template.
- [x] Added scripts/evaluate_faithfulness_judge.py.
- [ ] Label the human validation subset.
- [ ] Compare judge vs human labels.
- [ ] Record accuracy, precision, recall, F1, and failure cases.
- [ ] Freeze judge configuration for published answer-level evaluation.

### 2.6 Answer-level evaluation

- [x] Existing retrieval/citation/faithfulness dimensions remain separate.
- [x] Evaluation documentation explicitly rejects a single collapsed quality score.
- [ ] Create a held-out answer-evaluation set.
- [ ] Schedule repeatable answer-level evaluation using the frozen benchmark/judge configuration.
- [ ] Report citation validity, answer relevance, faithfulness, and operational latency separately.

### Phase 2 gate

Implemented:

- [x] Evaluation schema.
- [x] Unbiased pooling mechanism.
- [x] nDCG.
- [x] Bootstrap statistics.
- [x] Controlled Dense-vs-Hybrid experiment harness.
- [x] Faithfulness judge metadata and human-validation harness.

Still required before declaring Phase 2 closed:

- [ ] 50–100 final labeled queries.
- [x] Frozen CHA corpus hash recorded; configuration hash remains pending until benchmark freeze.
- [ ] Human-judged Dense ∪ BM25 pool.
- [ ] Dense-vs-Hybrid experiment execution.
- [ ] Failure analysis/case studies.
- [ ] Human validation of faithfulness judge.
- [ ] Held-out answer-level evaluation.

**Phase 3 production data migration should wait until the retrieval benchmark is frozen, even though the Phase 3 schema can be designed in parallel.**

# 6. Phase 3 — Production Data Layer: Supabase + pgvector

**Status: [~] REFERENCE SCHEMA IMPLEMENTED; LIVE PROJECT + VERIFICATION PENDING**

## Objective

Replace local-only persistence/index assumptions with production-managed storage while preserving the existing retrieval architecture.

## 3.1 Supabase project

- [x] Production data model designed in `docs/DATABASE.md`.
- [x] Reviewed the connected Supabase account without modifying any project.
- [x] Confirmed the only currently visible project is unrelated `Tackboard`; it is explicitly excluded.
- [ ] Identify/create the dedicated Enterprise RAG Supabase project.
- [ ] Configure environment variables.
- [ ] Establish development/staging separation where practical.

## 3.2 Database schema

- [x] Added reviewed reference DDL at `supabase/schema.sql`.
- [x] `organizations` + `organization_members`.
- [x] `documents` with content-hash/pipeline-version idempotency.
- [x] `document_chunks` with page/span metadata and embedding provenance.
- [x] `ingestion_jobs` with worker leasing fields.
- [x] `conversations`, `messages`, `answers`, `citations`.
- [x] `retrieval_runs` telemetry model.
- [ ] Generate the real migration filename with the installed Supabase CLI once the target project is selected.
- [ ] Apply migration to the dedicated project.
- [ ] Verify schema against the live database.
- [x] Added application persistence entities and repository interfaces decoupled from Supabase/Postgres.
- [x] Added in-memory repository adapters for deterministic unit tests and local boundary validation.

## 3.3 Application persistence boundary

- [x] Domain persistence records defined in `app/persistence/entities.py`.
- [x] Repository contracts defined in `app/persistence/repositories.py`.
- [x] In-memory adapters added for tests without requiring a live database.
- [ ] Implement the Postgres/Supabase repository adapter after the target project is selected.
- [ ] Wire query/ingestion services through repository interfaces rather than direct database calls.

## 3.4 pgvector

- [x] Reference schema enables the `vector` extension in the `extensions` schema.
- [x] Current baseline target is 384-dimensional `all-MiniLM-L6-v2`.
- [x] Reference HNSW index uses `vector_cosine_ops`.
- [x] Reference similarity function uses cosine distance and `security invoker`.
- [ ] Verify the live project's pgvector/Postgres versions.
- [ ] Store production embeddings.
- [ ] Validate top-k parity against the local FAISS baseline.
- [ ] Benchmark latency and filtered-search behavior.

## 3.5 Source storage

- [ ] Configure Supabase Storage on the dedicated project.
- [ ] Store uploaded PDFs.
- [ ] Store document metadata/path.
- [ ] Define file lifecycle/deletion behavior.
- [ ] Add Storage RLS/policy tests.

## 3.6 BM25 strategy

Phase 1 selected the tenant-safe architecture.

- [x] Per-tenant BM25 indexes selected.
- [x] Global BM25 plus post-filtering rejected.
- [ ] Implement tenant-scoped lexical index lifecycle.
- [ ] Define index refresh/rebuild behavior in the worker.
- [ ] Define deletion/invalidation behavior.
- [ ] Measure operational complexity.
- [ ] Re-run the relevant retrieval comparison under the production lexical strategy.

Do not assume that a global BM25 index plus post-filtering is safe for multi-tenant production.

### Phase 3 gate

- [x] Application persistence boundary is defined and unit-tested without a live database.
- [ ] Upload → DB → chunk → embedding flow works on the dedicated project.
- [ ] pgvector retrieval matches the expected FAISS baseline.
- [ ] Source PDFs persist correctly.
- [ ] Data model supports tested multi-user isolation.
- [ ] No production secrets are exposed.

---

# 7. Phase 4 — Authentication + Authorization + RLS

**Status: [ ] PENDING**

## Objective

Make the application safely multi-user.

### Authentication

- [ ] Supabase Auth.
- [ ] Email/password.
- [ ] Magic link.
- [ ] Add OAuth providers later if needed.

### Authorization

- [ ] User owns/has access to documents.
- [ ] User owns conversations.
- [ ] Retrieval is scoped to authorized documents.
- [ ] API validates JWT.
- [ ] Server never trusts client-supplied ownership IDs.

### Row Level Security

- [ ] Enable RLS.
- [ ] Policies for documents.
- [ ] Policies for chunks.
- [ ] Policies for conversations/messages.
- [ ] Policies for citations/answers.
- [ ] Policies for organization/tenant membership.

### Service-role / RLS test

- [ ] Verify the API request path carries the correct user authorization context.
- [ ] Verify RLS behavior through the actual application path.
- [ ] If service-role access exists, separately test application-layer authorization and explicitly document why that operation bypasses RLS.

### Security test

- [ ] User A cannot retrieve User B's documents.
- [ ] User A cannot access User B's source PDFs.
- [ ] User A cannot manipulate another user's conversation IDs.
- [ ] Unauthorized API requests fail safely.

### Phase 4 gate

**RLS isolation must be tested before production user data is accepted.**

---

# 8. Phase 5 — Production Ingestion Pipeline

**Status: [ ] PENDING**

## Objective

Create a reliable document ingestion lifecycle.

## Flow

```
Upload PDF
   ↓
Storage
   ↓
Document record
   ↓
Processing job
   ↓
Text extraction
   ↓
OCR fallback
   ↓
Chunking
   ↓
Metadata
   ↓
Embeddings
   ↓
Dense index
   ↓
BM25 index
   ↓
READY
```

### Document states

- [ ] UPLOADED
- [ ] PROCESSING
- [ ] INDEXING
- [ ] READY
- [ ] FAILED

### Parsing

- [x] Native PDF extraction exists.
- [x] OCR fallback for low-text/scanned PDF pages.
- [x] Scanned-PDF detection via native-text threshold.
- [ ] Extraction error handling.
- [ ] Large-document handling.

### Document identity

- [ ] Compute a content hash for uploaded documents.
- [ ] Deduplicate identical documents.
- [ ] Define behavior for same-content re-upload.
- [ ] Keep source-document identity separate from chunk/index identity.

### Chunking

- [x] Recursive chunking exists.
- [ ] Semantic chunking evaluation.
- [ ] Stable deterministic chunk IDs.
- [ ] Metadata preservation.
- [ ] Chunking benchmark.

### Async execution

Use the mechanism selected during Phase 1.

- [ ] Do not parse/embed large documents inside the upload request.
- [ ] Implement the selected queue/worker architecture.
- [ ] Persist job status.
- [ ] Retry failed jobs.
- [ ] Make jobs idempotent.
- [ ] Add job ownership/tenant context.
- [ ] Ensure failed jobs cannot partially expose another tenant's data.

### Phase 5 gate

A user can upload a document and reliably receive a **READY / FAILED** outcome without holding the HTTP request open for the entire indexing operation.

---

# 9. Phase 6 — Production Query + Conversation System

**Status: [ ] PENDING**

## Objective

Convert the development query pipeline into a persistent authenticated product workflow.

## Query flow

```
JWT
 ↓
Authorization
 ↓
Validate query
 ↓
Optional query rewriting
 ↓
Metadata filters
 ↓
Dense retrieval
 ↓
BM25 retrieval
 ↓
RRF fusion
 ↓
Cross-encoder reranking
 ↓
Context assembly
 ↓
LLM generation
 ↓
Citation mapping
 ↓
Citation verification
 ↓
Faithfulness verification
 ↓
Persist result
 ↓
Response
```

### Query rewriting

- [ ] Implement as an explicit stage.
- [ ] Keep original query.
- [ ] Store rewritten query.
- [ ] Evaluate whether rewriting improves retrieval.
- [ ] Do not add it merely because it is fashionable.

### Conversations

- [ ] Conversations table.
- [ ] Messages table.
- [ ] Answers table.
- [ ] Citation relationships.
- [ ] Create chat.
- [ ] Rename chat.
- [ ] Delete chat.
- [ ] Continue chat.
- [ ] History.

### Evidence-first response

The UI/API should expose:

- [ ] Answer.
- [ ] Source IDs.
- [ ] Document.
- [ ] Page.
- [ ] Chunk.
- [ ] Retrieved passage.
- [ ] Citation validity.
- [ ] Faithfulness result.
- [ ] Retrieval mode.
- [ ] Pipeline timing.

### Phase 6 gate

Authenticated user can:

**login → upload → wait for indexing → ask → receive grounded answer → inspect evidence → return to history.**

---

# 10. Phase 7 — Vercel Deployment + CI/CD + Security + Observability

**Status: [ ] PENDING**

## Objective

Deploy the product safely and establish an operational baseline.

## Vercel

- [ ] Production project.
- [ ] Frontend deployment.
- [ ] Backend/API deployment strategy.
- [ ] Environment variables.
- [ ] Preview deployments.
- [ ] Production deployment.

### Critical architecture test

The current system loads ML models at startup. Before putting the FastAPI inference path directly into Vercel Functions:

- [ ] Measure bundle size.
- [ ] Measure cold start.
- [ ] Measure memory.
- [ ] Measure execution duration.
- [ ] Measure concurrent requests.
- [ ] Measure model loading cost.

If the workload is unsuitable:

- [ ] Keep frontend/API on Vercel.
- [ ] Move heavy inference/reranking to an appropriate long-running service.
- [ ] Keep the architecture modular.

## CI/CD

- [ ] GitHub Actions.
- [ ] Lint.
- [ ] Unit tests.
- [ ] Integration tests.
- [ ] Frontend build.
- [ ] API smoke test.
- [ ] Evaluation smoke test.
- [ ] Deployment gate.

## Security

- [ ] Strict CORS.
- [ ] Prompt-injection handling for uploaded documents.
- [ ] Treat retrieved document text as untrusted data.
- [ ] Prevent retrieved content from overriding system/developer instructions.
- [ ] Sanitize/structure evidence passed to the generation model.
- [ ] Add adversarial prompt-injection test cases.

### Abuse controls

- [ ] Per-user request rate limits.
- [ ] Per-user token quotas.
- [ ] Per-user estimated-cost quotas.
- [ ] Storage/upload quotas.

### Request security

- [ ] Input validation.
- [ ] Input validation.
- [ ] PDF type validation.
- [ ] File-size limits.
- [ ] Rate limiting.
- [ ] Request-size limits.
- [ ] Secret isolation.
- [ ] Safe error responses.
- [ ] No stack traces in production.
- [ ] Safe logging.
- [ ] Abuse protection.
- [ ] RLS verification.

Never expose provider keys through public frontend environment variables.

## Observability

Persist:

- [ ] retrieval latency
- [ ] reranking latency
- [ ] generation latency
- [ ] faithfulness latency
- [ ] total latency
- [ ] input/output tokens
- [ ] estimated cost
- [ ] quota usage / remaining budget
- [ ] retrieved count
- [ ] reranked count
- [ ] citation validity
- [ ] faithfulness result
- [ ] errors

### Phase 7 gate

Production deployment must pass automated health, API, auth, RLS, and browser smoke tests.

---

# 11. Phase 8 — Product UX + QA + Release

**Status: [ ] PENDING**

## UX

- [ ] Responsive layout.
- [ ] Authentication screens.
- [ ] Document management.
- [ ] Upload progress.
- [ ] Indexing state.
- [ ] Chat interface.
- [ ] Source/evidence panel.
- [ ] Conversation history.
- [ ] Empty states.
- [ ] Loading states.
- [ ] Error states.
- [ ] Retry behavior.
- [ ] Copy answer.
- [ ] Copy citation/source.
- [ ] Source document preview.
- [ ] Settings/logout.

## Testing

### Backend

- [ ] Parser tests.
- [ ] OCR tests.
- [ ] Chunking tests.
- [ ] Dense retrieval tests.
- [ ] BM25 tests.
- [ ] Hybrid tests.
- [ ] Reranker tests.
- [ ] Citation tests.
- [ ] Faithfulness tests.
- [ ] API tests.
- [ ] Auth tests.
- [ ] RLS tests.
- [ ] Storage tests.
- [ ] Database integration tests.

### Frontend

- [ ] Production build.
- [ ] Authentication flow.
- [ ] Upload flow.
- [ ] Query flow.
- [ ] Citation inspection.
- [ ] Conversation history.
- [ ] Error handling.

### End-to-end browser smoke

```
Sign up
  ↓
Login
  ↓
Upload document
  ↓
Wait for READY
  ↓
Ask question
  ↓
Read answer
  ↓
Open citation
  ↓
Inspect evidence
  ↓
Open history
  ↓
Logout
```

## Release documentation

- [ ] README
- [ ] ARCHITECTURE
- [ ] DATABASE
- [ ] API
- [ ] EVALUATION
- [ ] DEPLOYMENT
- [ ] SECURITY
- [ ] CHANGELOG

### Final release gate

All critical paths must pass:

```
Engine ✓
Evaluation ✓
Persistence ✓
Auth ✓
RLS ✓
Ingestion ✓
Query ✓
Citations ✓
Faithfulness ✓
Deployment ✓
Security ✓
Browser QA ✓
Documentation ✓
```

---

# 12. Cross-Phase Technical Decisions

## Do not do yet

- [ ] Do not redesign the retrieval architecture without benchmark evidence.
- [ ] Do not remove BM25 without measuring its contribution.
- [ ] Do not add query rewriting without evaluating it.
- [ ] Do not claim hybrid retrieval is superior before the controlled experiment.
- [ ] Do not claim production readiness before deployment/resource testing.
- [ ] Do not move heavy ML inference to Vercel blindly.
- [ ] Do not expose local development scores as benchmark results.

## Preserve

- [x] Modular retrieval components.
- [x] Explicit retrieval stages.
- [x] Citation traceability.
- [x] Faithfulness evaluation.
- [x] Pipeline observability.
- [x] Evidence-first product positioning.

---

# 13. Cross-Phase Execution Rule

The phase checklists above are the **single source of truth**. Do not maintain a second numbered execution checklist.

The dependency order is:

```
Phase 0
  ↓
Phase 1
  ├── reproducibility + minimal CI
  ├── Vercel/inference feasibility
  ├── async worker architecture
  ├── tenant-safe BM25 strategy
  └── Supabase JWT/RLS strategy
  ↓
Phase 2
  ├── versioned span/page-level evaluation
  ├── unbiased relevance pooling
  ├── Dense vs Hybrid benchmark
  ├── confidence intervals / paired comparisons
  └── answer + faithfulness judge validation
  ↓
Phase 3 — Supabase/pgvector/Storage
  ↓
Phase 4 — Auth/RLS
  ↓
Phase 5 — Async ingestion/OCR/indexing
  ↓
Phase 6 — Query/conversations
  ↓
Phase 7 — Deployment/security/observability
  ↓
Phase 8 — Product QA/release
```

Production architecture decisions made in Phase 1 constrain implementation in Phases 3–6; they must not be deferred until Phase 7.

---

# 14. Definition of Done

Enterprise RAG is considered **production-ready** only when:

- [ ] Retrieval quality is measured on a frozen labeled dataset.
- [ ] Dense and Hybrid retrieval have been fairly evaluated.
- [ ] Failure modes are documented.
- [ ] Dependencies are reproducible.
- [ ] Documents persist in Supabase.
- [ ] Dense retrieval works through pgvector.
- [ ] BM25 remains operational and measurable.
- [ ] Users authenticate.
- [ ] RLS prevents cross-user data access.
- [ ] Upload/indexing is asynchronous and reliable.
- [ ] Query results and conversations persist.
- [ ] Citations resolve to real evidence.
- [ ] Faithfulness verification is operational.
- [ ] Token/cost/latency telemetry is available.
- [ ] Vercel deployment has passed resource tests.
- [ ] CI/CD gates changes.
- [ ] Security controls are tested.
- [ ] Browser end-to-end flow passes.
- [ ] Production documentation is complete.

**Current position: Phase 2 empirical benchmark is active. The real 50-query CHA Dense ∪ BM25 pool is frozen, while silver labeling is quota-limited and human review remains pending. Phase 3 database design is being prepared in parallel without applying production schema changes.**
