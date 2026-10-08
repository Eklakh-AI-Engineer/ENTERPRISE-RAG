# Enterprise RAG — Evaluation

**Status:** Active evaluation contract  
**Last reviewed:** 2026-10-05

This document defines how retrieval, generation, citations, and faithfulness are evaluated. Benchmark numbers below are from the frozen evaluation set and identify their configuration and separate experimental artifact.

## 1. Evaluation layers

### Retrieval

| Metric | Purpose |
|---|---|
| Recall@1 / @5 / @10 | Relevant evidence in top-k |
| MRR | Rank of the first relevant result |
| nDCG@5 / @10 | Graded ranking quality |
| Precision@5 | Relevant results in top five |
| Retrieval latency | Retrieval cost |
| Reranking latency | Cross-encoder cost |

### Generation

Measures whether the answer addresses the information need correctly. Generation quality is reported separately from retrieval quality.

### Citation

Track:

- citation validity;
- citation accuracy;
- citation coverage;
- invalid citation rate.

### Faithfulness

For claim-level evaluation:

- total claims;
- supported claims;
- unsupported claims;
- faithfulness rate.

## 2. Golden benchmark

The active corpus is the versioned CHA policy corpus registered in data/evaluation/cha_corpus_manifest.json.

The repository contains **50 corpus-derived queries across 10 categories** in:

    data/evaluation/golden_queries_v1.json

Current status:

    50 queries
    10 categories
    frozen
    780 human relevance judgments

This is the **frozen human-verified benchmark**. The 780 judgments are stored in `data/evaluation/human_labels_v1.json` as an immutable compact score vector.

The existing cha_silver_labels_v1.json contains model-generated silver judgments. It must not be represented as human ground truth.

### Human annotation gate (completed)

For each query:

1. Retrieve the Dense ∪ BM25 candidate pool from the frozen corpus.
2. Review the pooled candidates.
3. Assign relevance:
   - **0** — not relevant;
   - **1** — marginal/background;
   - **2** — relevant evidence;
   - **3** — highly relevant/directly answers.
4. Record durable document_id, page, start_char, and end_char.
5. Set answerable.
6. The full set has now been reviewed: 780/780 candidates received human relevance grades and 780/780 provenance checks are marked verified.

Validate:

    python -m scripts.validate_golden_set

The benchmark runner expands the compact human-label artifact against the frozen candidate pool and refuses to execute if its checksum or judgment count does not match.

### MRR saturation finding

MRR is exactly 1.0 for Dense, BM25, Hybrid, and Reranker because the first retrieved result is relevant for every query/system pair. This is a property of the frozen benchmark, not evidence that the systems are equivalent. MRR is therefore reported for completeness but excluded from comparative claims. The next evaluation layer is the separate held-out challenge set.

## 3. Controlled retrieval comparison

Run the same corpus, queries, relevance judgments, chunking, and evaluation procedure for:

1. Dense
2. BM25
3. Hybrid/RRF
4. Hybrid/RRF + Cross-Encoder

Runner:

    python -m scripts.run_golden_retrieval_benchmark --benchmark data/evaluation/golden_queries_v1.json --chunks data/processed/cha_chunks.json --pool data/evaluation/cha_pool_v1.json --systems dense bm25 hybrid reranker --top-k 10 --candidate-k 20 --output data/evaluation/results/golden_v1.json

## Ingestion validation gates

**Stable evidence metadata: COMPLETE.** The chunk/ingestion gate requires a non-empty document and chunk identity, positive page and chunk index, canonical document-page-index identity, unique chunk IDs, valid integer spans within the source page, and exact agreement between each span and its page-text slice. Available section metadata is preserved. Citation mapping runs the structural gate and rejects unresolved source markers rather than silently omitting them. Deterministic repeated-input and deliberately corrupted-metadata cases are covered by `tests/test_evidence_metadata.py`.

**OCR fallback validation: COMPLETE.** Pages with sufficient native text do not invoke OCR. Insufficient pages attempt OCR; only sufficiently long, text-like, materially better OCR is accepted. Empty/poor results retain native text. OCR exceptions retain native text and record `extraction_status="ocr_failed"` plus `extraction_error`. Parser tests assert page/document identity and downstream chunk spans.

## Paired query-rewriting experiment

Artifact: `data/evaluation/results/golden_v1_query_rewriting.json`. Baseline and treatment both use Hybrid/RRF candidate retrieval plus the same cross-encoder, `top_k=10`, `candidate_k=20`, and the same materialized frozen human judgments. Rewrite strategy `strip-interrogative-prefix-v1` removes only a recognized leading question frame and preserves the remaining query body verbatim. The runtime flag defaults off.

| Metric | Baseline | Rewritten | Absolute delta | Relative delta |
|---|---:|---:|---:|---:|
| Recall@5 | 0.314451 | 0.317589 | +0.003138 | +0.998% |
| Recall@10 | 0.510629 | 0.509977 | -0.000653 | -0.128% |
| MRR | 1.000000 | 1.000000 | 0.000000 | 0.000% |
| nDCG@5 | 0.754794 | 0.750950 | -0.003844 | -0.509% |
| nDCG@10 | 0.744924 | 0.741851 | -0.003074 | -0.413% |

The per-query retrieval results and all baseline/treatment metrics are in the artifact. On nDCG@10, 13 queries improved (CHA-003, CHA-004, CHA-009, CHA-012, CHA-018, CHA-022, CHA-028, CHA-034, CHA-035, CHA-037, CHA-039, CHA-041, CHA-043), 28 were unchanged (CHA-002, CHA-007, CHA-008, CHA-011, CHA-013, CHA-014, CHA-016, CHA-017, CHA-019, CHA-020, CHA-021, CHA-024, CHA-025, CHA-027, CHA-029, CHA-030, CHA-031, CHA-032, CHA-033, CHA-036, CHA-038, CHA-040, CHA-042, CHA-044, CHA-045, CHA-046, CHA-047, CHA-048), and 9 degraded (CHA-001, CHA-005, CHA-006, CHA-010, CHA-015, CHA-023, CHA-026, CHA-049, CHA-050). The artifact includes original and rewritten text for all 50.

Category comparison deltas (rewritten minus baseline):

| Category | Recall@5 | Recall@10 | MRR | nDCG@10 | Result |
|---|---:|---:|---:|---:|---|
| Business Expense & Travel | -0.020000 | 0.000000 | 0.000000 | -0.004787 | Degraded |
| Compensation & Benefits | -0.004762 | 0.000000 | 0.000000 | -0.004947 | Degraded |
| Drug, Alcohol & Workplace Safety | 0.000000 | -0.014286 | 0.000000 | +0.001274 | Improved |
| Employee Relations & Conduct | +0.011111 | -0.023746 | 0.000000 | -0.046975 | Degraded |
| Equal Employment & Accommodation | 0.000000 | +0.008696 | 0.000000 | +0.008836 | Improved |
| Ethics, Investigations & Compliance | +0.022807 | 0.000000 | 0.000000 | -0.002228 | Degraded |
| Information Security | 0.000000 | +0.013333 | 0.000000 | +0.020835 | Improved |
| Leave & Time Off | 0.000000 | +0.009474 | 0.000000 | -0.006529 | Degraded |
| Procurement | +0.022222 | 0.000000 | 0.000000 | +0.002142 | Improved |
| Work Environment & Equipment | 0.000000 | 0.000000 | 0.000000 | +0.001644 | Improved |

Conclusion: results are mixed, with an aggregate nDCG regression and meaningful query/category regressions. Keep rewriting disabled and experimental; do not promote it based on the Recall@5 increase alone. Latency is recorded in the artifact but is runtime-sensitive and is not treated as evidence of retrieval-quality change.

## 4. Reproducibility contract

A benchmark result is defined by:

    Corpus
     + Query Set
     + Relevance Judgments
     + Chunking / Index Configuration
     + Model Versions
     + Retrieval Settings
     + Runtime Conditions
     = Benchmark Result

Record benchmark/configuration versions whenever any material input changes.

## 5. Held-out challenge and unanswerable evaluation

`data/evaluation/challenge_queries_v1.json` contains 20 independently authored queries kept separate from the frozen 50-query gold benchmark:

- 10 hard in-domain, corpus-blind queries with `answerable=null` pending human adjudication;
- 10 deliberately external/unanswerable controls with `answerable=false`.

Do not add these queries to the frozen gold result until they have been independently adjudicated and labeled. This prevents benchmark contamination and avoids guessed relevance labels.

For generated responses, `scripts/evaluate_answerability.py` reports the **insufficient-evidence rate** on the unanswerable controls and the false-abstention rate on adjudicated answerable queries.

Expected behavior:

- identify insufficient evidence;
- avoid unsupported factual claims;
- avoid citing unrelated evidence as authoritative.

Negative cases are analyzed separately from ordinary retrieval accuracy.

## 6. Faithfulness judge validation

The faithfulness judge is implemented, but its automated output is **not human-validated yet**. `data/evaluation/faithfulness_human_subset.schema.json` defines the independent review contract. The validation subset must contain at least 30 claims, with a human binary support label and the frozen judge output for each claim.

Run:

    python -m scripts.evaluate_faithfulness_judge --labels data/evaluation/faithfulness_human_subset.json

The validator reports accuracy, precision, recall, F1, and **Cohen's kappa**. Human labels remain the ground truth. Do not report a validated judge-agreement figure until this file contains real independently reviewed items.

## 7. Reproducibility configuration

| Layer | Configuration |
|---|---|
| Python | 3.12 |
| Corpus | `CHA-POLICY-CORPUS-V1` |
| Query set | `enterprise-rag-golden-v1-human-verified`, 50 queries |
| Chunker | `recursive-v2-span` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Dense index | FAISS `IndexFlatIP`, normalized vectors |
| BM25 | `rank-bm25==0.2.2` |
| Fusion | RRF |
| Candidate / top-k | 20 / 10 |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Bootstrap | 10,000 iterations, seed 42 |
| Generation | OpenRouter, model frozen per answer-evaluation artifact via `OPENROUTER_MODEL` |
| Faithfulness judge | same configured OpenRouter model, prompt `faithfulness-v1`, temperature 0 |
| Dependencies | `requirements.txt`, `requirements-dev.txt`, `requirements.lock` |

## 8. Error analysis

Classify retrieval failures where practical:

- lexical mismatch;
- semantic mismatch;
- identifier/entity mismatch;
- acronym mismatch;
- chunk-boundary failure;
- metadata/filtering failure;
- multi-hop failure;
- corpus coverage failure.

A failure record should retain the query, expected evidence, retrieved evidence, configuration, and diagnosis.

## 9. Statistical reporting

For paired Dense-vs-Hybrid comparisons, report query-level deltas and bootstrap confidence intervals.

Point estimates without query-level comparison are insufficient evidence for a retrieval improvement.

## 10. Result discipline

Do not publish:

- development-run metrics as benchmark numbers;
- MRR=1.0 as evidence that one retrieval system is superior;
- automated faithfulness scores as human-validated without Cohen's kappa;
- AI-generated silver labels as human gold;
- a benchmark result without a frozen corpus/query/label configuration.

Change retrieval architecture **after** measurement and failure analysis, not before.
