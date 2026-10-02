# Enterprise RAG — Project Audit & Resume Point

**Audit date:** 2026-10-02  
**Repository:** Eklakh-AI-Engineer/ENTERPRISE-RAG  
**Branch:** main  
**Audited HEAD:** b0c92a84a252cbf7b6cec74d4b8547a1ece23086  
**Status:** PAUSED AT A VALID RESUME POINT

> This audit supersedes the 2026-10-01 pause-point snapshot for execution status. It distinguishes implemented engineering work from work that is actually verified in production.

## 1. Executive summary

Enterprise RAG is now substantially beyond a basic RAG demo. The repository contains dense retrieval, BM25, hybrid/RRF retrieval, cross-encoder reranking, evidence-grounded generation, citations/faithfulness infrastructure, evaluation tooling, Supabase/Postgres/pgvector persistence, tenant-scoped vector retrieval, authentication boundaries, RLS/Storage design, and an asynchronous ingestion worker architecture.

It is **not yet a production-ready multi-tenant RAG product**.

There are two parallel tracks:

1. **Phase 2 evaluation:** finish silver labels, human-review them, freeze the benchmark, run Dense-vs-Hybrid and answer/faithfulness evaluation.
2. **Production path:** prove Auth/RLS isolation, complete live ingestion, production BM25, production query integration, deployment and security hardening.

## 2. Current scorecard

| Area | State |
|---|---|
| Dense retrieval | DONE |
| BM25 retrieval | DONE locally; production lifecycle NOT DONE |
| Hybrid + RRF | DONE locally |
| Cross-encoder reranking | DONE |
| Evidence/citations/faithfulness infrastructure | DONE |
| PDF native extraction + OCR fallback | DONE in code; production validation pending |
| Recursive chunking + page/span metadata | DONE |
| Semantic chunking | NOT DONE |
| Phase 2 evaluation harness | DONE |
| CHA corpus/pool | FROZEN: 50 queries / 780 candidates |
| Silver labels | IN PROGRESS: 168/780 |
| Human final relevance labels | NOT DONE |
| Dense-vs-Hybrid experiment | NOT RUN |
| Faithfulness human validation | NOT DONE |
| Supabase schema + pgvector | DONE |
| Tenant-scoped vector RPC | DONE |
| RLS policies | IMPLEMENTED; live two-user proof pending |
| Real Auth users | NOT DONE |
| Authenticated upload | NOT DONE as final production API flow |
| Live ingestion execution | NOT VERIFIED |
| Chunk replacement idempotency | NOT DONE |
| Production BM25 lifecycle | NOT DONE |
| Production query path | NOT DONE |
| Deployment | NOT DONE |
| Production security hardening | NOT DONE |
| CI | CONFIGURED; current HEAD has no reported combined status |

## 3. Phase 2 exact state

Frozen CHA corpus:

- Business Expense
- Employee Handbook 2025
- Information Security
- Procurement

Corpus hash:

`c85eaf4bd9a958f1864f4c030be5ea04f69faf20a3c011cf50239b67cf1fccc0`

Candidate pool:

- 50 queries
- 780 candidates
- Dense ∪ BM25 pooling
- source/rank/score provenance preserved

Current silver artifact:

`data/evaluation/cha_silver_labels_v1.json`

Current state:

- **168 / 780 judgments complete**
- **10 / 50 queries fully complete**
- **CHA-011 partially labeled and checkpointed**
- **612 judgments remaining**
- model: `nvidia/nemotron-3.5-lightning:free`
- latest stop reason: OpenRouter HTTP 429

Completed queries: CHA-001 through CHA-010.

The silver labels are **AI-generated silver judgments, not final human ground truth**. Final relevance labels must retain silver vs human provenance.

### Silver workflow improvements

The workflow now:

- uses batch size 4;
- validates missing/duplicate candidate indices;
- handles empty/non-text model responses;
- retries malformed batches;
- checkpoints after successful batches;
- persists partial queries;
- stops cleanly on HTTP 429;
- resumes without redoing completed work;
- enforces judge-model provenance.

This architecture was validated by workflow run #11: the run completed successfully while the labeling artifact recorded a clean rate-limited stop and preserved progress.

## 4. Production database / Supabase

A dedicated Enterprise RAG Supabase project exists separately from Tackboard.

Implemented/live architecture includes:

- organizations and memberships;
- documents;
- document_chunks;
- ingestion_jobs;
- conversations/messages;
- answers/citations;
- retrieval_runs;
- pgvector;
- RLS;
- private document Storage;
- Storage policies;
- atomic ingestion-job claim RPC;
- tenant-scoped vector-search RPC.

The previous unscoped vector-search overload was removed.

### Security verification still required

- [ ] Create real Auth User A
- [ ] Create real Auth User B
- [ ] Create organizations/memberships
- [ ] Test cross-tenant document denial
- [ ] Test cross-tenant chunk/retrieval denial
- [ ] Test Storage isolation
- [ ] Test conversation isolation
- [ ] Test forged organization IDs
- [ ] Test RLS through actual authenticated clients

Until these are demonstrated, do not call the system fully multi-tenant or RLS-verified.

## 5. Production ingestion

Implemented components:

`PENDING → PROCESSING → INDEXING → READY / FAILED`

with atomic job claiming, leases, retry state, Storage abstraction, PDF/OCR parsing, recursive chunking, embeddings, pgvector persistence, worker orchestration and tests.

Still required:

- live authenticated upload;
- live worker execution;
- background worker deployment;
- long-document lease/heartbeat strategy;
- concurrent-worker integration testing;
- operational monitoring;
- production BM25 integration.

### Critical indexing caveat

Current Supabase chunk persistence is an **upsert**, not an atomic replacement.

If re-ingestion produces fewer/different chunks, stale chunks can remain.

Before production indexing is declared complete, implement one of:

- transactional delete + insert;
- versioned chunks with active-version selection;
- atomic replacement RPC.

## 6. Production BM25

The selected production strategy is **per-tenant BM25 indexes**.

Still required:

- durable tenant lexical corpus;
- index creation;
- refresh/rebuild;
- deletion/invalidation;
- version activation;
- worker integration;
- benchmark.

Do not replace this with global BM25 + post-filtering for production multi-tenancy.

## 7. Production query path

The intended path is:

`JWT → tenant authorization → pgvector + tenant BM25 → RRF → reranker → evidence → OpenRouter generation → citations → verification → faithfulness → persistence`

The current query endpoint has **not** been switched to this production path. It still uses the existing local QueryPipeline.

Therefore do not claim production tenant-aware querying, production hybrid retrieval, or end-to-end persistent RAG yet.

## 8. Evaluation remaining

Phase 2 is not closed until:

- [ ] silver labels reach 780/780;
- [ ] human review/correction is complete;
- [ ] final relevance judgments are frozen;
- [ ] benchmark/configuration hash is frozen;
- [ ] Dense-vs-Hybrid experiment is executed;
- [ ] raw experiment artifact is published;
- [ ] query/category failure analysis is completed;
- [ ] retrieval case studies are documented;
- [ ] faithfulness judge is human-validated;
- [ ] held-out answer evaluation is run;
- [ ] final evaluation report is produced.

Do not claim Hybrid retrieval has been experimentally proven superior until those steps are complete.

## 9. Repository state since the previous audit

Compared with the 2026-10-01 audit point, the meaningful changes are concentrated in Phase 2:

- Nemotron free-model switch;
- judge-model provenance enforcement;
- malformed-response resilience;
- batch-level silver checkpointing;
- 168 silver judgments accumulated;
- current audit/resume state.

Current HEAD:

`b0c92a84a252cbf7b6cec74d4b8547a1ece23086`

The current GitHub combined-status endpoint reports no status entries. CI therefore remains **configured but unverified**.

## 10. What is safe to claim

Accurate project description:

> Enterprise RAG is a retrieval-engineering system with dense/BM25/hybrid retrieval, reranking, evidence-grounded generation, evaluation infrastructure, and a production-oriented Supabase/pgvector multi-tenant architecture. The final evaluation evidence and production application path are still being completed and validated.

Do not claim:

- production-ready;
- fully multi-tenant;
- fully RLS-verified;
- production-deployed;
- benchmark-proven;
- Hybrid retrieval proven superior;
- end-to-end authenticated;
- production query path complete.

## 11. Resume order

### Track A — Phase 2

1. Continue from CHA-011 partial checkpoint.
2. Reach 780/780.
3. Human-review/correct labels.
4. Freeze benchmark.
5. Run Dense-vs-Hybrid.
6. Failure analysis.
7. Faithfulness validation.
8. Held-out answer evaluation.

### Track B — production

1. Create two real Auth test users.
2. Verify RLS and Storage isolation.
3. Finish authenticated document upload.
4. Execute live ingestion.
5. Fix atomic chunk replacement.
6. Benchmark FAISS vs pgvector.
7. Implement tenant BM25 lifecycle.
8. Switch QueryPipeline to production retrieval.
9. Persist answers/citations/retrieval telemetry end-to-end.
10. Deploy and harden security/observability.
11. Complete frontend product flow.

## 12. Current resume point

**Phase 2:** 168 / 780 silver judgments; CHA-011 partial checkpoint.

**Production security gate:** real two-user RLS isolation test.

**Immediate rule:** do not redesign the silver-label architecture again unless a new failure demonstrates a real defect. The current checkpoint architecture is working.

**Conclusion:** strong engineering foundation; evaluation, security verification, production ingestion/query integration, deployment, and final QA remain.
