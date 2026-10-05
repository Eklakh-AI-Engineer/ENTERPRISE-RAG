# Human Relevance Freeze — CHA Golden Benchmark v1

**Date:** 2026-10-05  
**Corpus:** CHA-POLICY-CORPUS-V1  
**Queries:** 50  
**Candidate judgments:** 780  
**Status:** Frozen

## Human-review result

All 780 candidates from the frozen Dense ∪ BM25 candidate pool were manually reviewed.

| Human grade | Count |
|---:|---:|
| 0 — Not relevant | 323 |
| 1 — Marginal/background | 266 |
| 2 — Relevant evidence | 82 |
| 3 — Highly relevant / directly answers | 109 |
| **Total** | **780** |

All 780 reviewed candidates have `Provenance Verified = Y`.

## Ground-truth policy

The human grades are the benchmark ground truth. The earlier silver-AI labels remain a development artifact and are not used as ground truth.

The compact artifact `data/evaluation/human_labels_v1.json` stores the 780 grades as a deterministic 2-bit-per-grade vector. Its candidate-order SHA-256 binds the vector to the exact Dense ∪ BM25 pool ordering. The benchmark runner expands this vector into normal document/page/character-span judgments before computing metrics.

## Comparison with silver labels

The original silver labels and human labels have **47.05% exact agreement** (367/780). This is diagnostic evidence that silver labels should not be substituted for human ground truth.

The workbook's **ChatGPT Proposed** column is not treated as an independent model evaluation result. It was produced by the earlier programmatic proposal heuristic and is retained only as a reviewer-assistance comparison.

## Reproducibility

The frozen benchmark is defined by:

- the versioned CHA corpus;
- the 50 fixed query definitions;
- the frozen Dense ∪ BM25 candidate pool;
- the immutable packed human-label vector;
- the candidate-order checksum;
- the existing retrieval benchmark configuration.

No retrieval quality numbers are published by this freeze alone. Dense, BM25, Hybrid/RRF, and reranker metrics must be produced by the benchmark runner under the controlled configuration.
