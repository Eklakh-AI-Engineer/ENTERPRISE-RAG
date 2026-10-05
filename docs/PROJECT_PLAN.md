# Enterprise RAG — Local-First Project Plan

**Active direction:** local retrieval-engineering product first; production deployment is a later release stage.

## 1. Current repository state

The repository now treats the following as the active system:

```
PDF
  -> parsing
  -> chunking + evidence metadata
  -> Dense retrieval + BM25
  -> Hybrid / RRF
  -> Cross-encoder reranking
  -> context assembly
  -> LLM generation
  -> citations
  -> faithfulness
  -> evaluation + observability
  -> React/Vite inspection UI
```

Production-specific Supabase/Railway implementation remains in Git history and the application boundary for later reuse, but it is not the current development gate.

## 2. Repository rules

- `tests/` is the canonical automated test suite.
- One-off `scripts/test_*.py` files are intentionally removed.
- Debug/diagnostic scripts are intentionally removed after their useful behavior was incorporated into the application/tests.
- Silver-label tooling is not treated as a gold-evaluation source.
- Evaluation artifacts must identify their corpus/query/benchmark version.
- No fabricated human relevance judgments.
- Production deployment work must not block local retrieval experiments.

## 3. Completion roadmap

### Phase A — Local baseline
- [ ] Clean local environment and startup commands.
- [ ] Run full backend test suite.
- [ ] Run frontend lint/build.
- [ ] Verify local PDF -> answer -> evidence flow.
- [ ] Remove remaining dead imports/configuration revealed by tests.

### Phase B — Ingestion quality
- [ ] Freeze PDF parser behavior.
- [x] Validate page/section/chunk metadata and stable IDs.
- [x] Validate character offsets and source-page text correspondence.
- [ ] Test malformed/empty PDFs.
- [ ] Evaluate chunk size/overlap.
- [x] Decide and evaluate OCR fallback; failures are explicit and observable.

**Evidence metadata gate: COMPLETE. OCR fallback validation: COMPLETE.** Automated coverage verifies required identity fields, positive pages, preserved sections, canonical IDs, duplicate detection, page bounds, text/span equality, citation resolution, and deterministic chunk identity. OCR tests cover native-only, fallback attempt, accepted OCR, rejected OCR, and OCR failure states.

### Phase C — Retrieval benchmark
- [x] Frozen CHA corpus/query pool exists.
- [ ] Human-verify the relevance pool.
- [ ] Freeze 50–100 gold queries.
- [ ] Record benchmark/configuration hashes.
- [ ] Run Dense, BM25, and Hybrid/RRF.
- [ ] Run Recall@5/@10, MRR, nDCG@5/@10.
- [ ] Add paired bootstrap confidence intervals to the published results.

### Phase D — Reranking and failure analysis
- [ ] Compare Hybrid vs Hybrid + CrossEncoder.
- [ ] Build query-level failure cases.
- [ ] Categorize retrieval failures.
- [ ] Tune only against the frozen benchmark.
- [ ] Re-run the benchmark after every material change.

### Phase E — Query rewriting
- [x] Implement rewriting as an explicit experimental toggle (disabled by default).
- [x] Compare original vs rewritten queries on the same frozen gold set.
- [x] Report gains and regressions by query category.
- [x] Keep rewriting results in a separate artifact from the baseline experiment.

**Experimental conclusion:** mixed, with aggregate nDCG@10 down 0.003074 (-0.413%), 13 queries improved, 9 degraded, and 28 unchanged. Five categories improved and five degraded. Keep rewriting experimental and disabled by default. See [the paired result artifact](../data/evaluation/results/golden_v1_query_rewriting.json) and [evaluation analysis](EVALUATION.md).

### Phase F — Answer/evidence evaluation
- [ ] Human-validate the faithfulness judge.
- [ ] Create held-out answer evaluation set.
- [ ] Measure citation validity and citation accuracy.
- [ ] Measure faithfulness separately from retrieval relevance.
- [ ] Record latency by pipeline stage.
- [ ] Record token usage and cost where provider metadata is available.

### Phase G — Local product freeze
- [ ] Upload PDF.
- [ ] Index document.
- [ ] Query knowledge base.
- [ ] Show answer and verifiable evidence.
- [ ] Show retrieval/evaluation metrics.
- [ ] Show latency.
- [ ] Complete responsive frontend QA.
- [ ] Write final README and results report.

### Phase H — Production release
Only after Phase G is frozen:
- [ ] Re-enable/finish Supabase persistence.
- [ ] Verify pgvector parity with local retrieval.
- [ ] Verify Storage lifecycle.
- [ ] Verify Auth/RLS and cross-tenant isolation.
- [ ] Make ingestion worker multi-tenant/reliable.
- [ ] Deploy FastAPI.
- [ ] Deploy frontend.
- [ ] Run authenticated production E2E.
- [ ] Add production observability/rate limits/quotas.
- [ ] Publish production architecture.

## 4. Definition of done

The local research product is complete when:

- a new PDF becomes searchable chunks with stable page/section/span metadata;
- Dense, BM25, Hybrid/RRF, and reranking are independently measurable;
- a 50–100 query human-verified gold set is frozen;
- Recall@5/@10, MRR, and nDCG@5/@10 are reproducible;
- Dense vs Hybrid is a controlled experiment;
- reranking and query rewriting are separately evaluated;
- citations are verifiable and unsupported citations are detected;
- faithfulness is quantitatively evaluated and its judge has a human validation subset;
- stage and end-to-end latency are recorded;
- token usage/cost is recorded where measurable;
- the local frontend demonstrates the complete evidence-grounded workflow.

## 5. What is deliberately out of scope for the current milestone

- Vercel deployment
- Railway deployment
- Supabase production migration
- production Storage
- production worker operation
- production multi-tenant release

These are release-stage tasks, not prerequisites for completing the retrieval-engineering research product.
