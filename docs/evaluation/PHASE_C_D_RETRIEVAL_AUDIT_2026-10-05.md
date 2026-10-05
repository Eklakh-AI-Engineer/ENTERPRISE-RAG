# Phase C/D Retrieval Audit — Frozen CHA Benchmark

**Audit date:** 2026-10-05  
**Benchmark artifact:** `data/evaluation/results/golden_v1.json`  
**Benchmark status:** Frozen  
**Corpus:** `CHA-POLICY-CORPUS-V1`  
**Queries:** 50  
**Human-graded pooled candidates:** 780  
**Systems:** Dense, BM25, Hybrid, Reranker  
**Configuration:** top-k=10, candidate-k=20, bootstrap iterations=10,000, seed=42

## 1. Audit scope

This document records the Phase C/D retrieval analysis performed against the frozen benchmark artifact. The audit intentionally did **not** modify retrieval code, benchmark labels, corpus data, query definitions, or retrieval parameters.

The purpose is to preserve the empirical result, statistical interpretation, failure analysis, and research conclusion in repository history.

## 2. Aggregate results

| System | Recall@5 | Recall@10 | MRR | nDCG@5 | nDCG@10 | Retrieval latency (ms) |
|---|---:|---:|---:|---:|---:|---:|
| Dense | 0.326767 | 0.491417 | 1.000000 | 0.724170 | 0.698555 | 15.3842 |
| BM25 | 0.328555 | 0.498463 | 1.000000 | 0.729654 | 0.714270 | 0.9756 |
| Hybrid | 0.330857 | 0.540096 | 1.000000 | 0.748303 | 0.747459 | 17.3338 |
| Reranker | 0.314451 | 0.510629 | 1.000000 | 0.754794 | 0.744924 | 1346.5022 |

### Key observations

- Hybrid is the best aggregate system on Recall@5 and Recall@10.
- Hybrid is better than Dense on nDCG@5 and nDCG@10.
- Reranker is best on nDCG@5, but slightly below Hybrid on nDCG@10.
- BM25 is by far the fastest retrieval system.
- Reranking introduces a very large latency cost.

## 3. Dense → Hybrid deltas

| Metric | Absolute delta | Percent delta |
|---|---:|---:|
| Recall@5 | +0.004090 | +1.2517% |
| Recall@10 | +0.048679 | +9.9059% |
| MRR | +0.000000 | 0.0000% |
| nDCG@5 | +0.024133 | +3.3325% |
| nDCG@10 | +0.048904 | +7.0007% |
| Retrieval latency | +1.9496 ms | +12.6727% |

The strongest aggregate gains are therefore at deeper retrieval depth: Recall@10 and nDCG@10.

## 4. Statistical significance

The benchmark's paired bootstrap analysis gives the following Dense → Hybrid 95% confidence intervals:

| Metric | Mean delta | 95% CI |
|---|---:|---:|
| Recall@5 | 0.004090 | [-0.018174, 0.029088] |
| Recall@10 | 0.048679 | [0.026467, 0.072413] |
| MRR | 0.000000 | [0.000000, 0.000000] |
| nDCG@5 | 0.024133 | [-0.019359, 0.068056] |
| nDCG@10 | 0.048904 | [0.020008, 0.078187] |

### Statistical conclusion

The Dense → Hybrid improvement is statistically supported for:

- **Recall@10**
- **nDCG@10**

The improvement is **not statistically decisive** for:

- Recall@5
- nDCG@5
- MRR

This means the correct research interpretation is a deeper-ranking/coverage improvement rather than a universal top-5 improvement.

## 5. MRR audit

MRR was separately audited before this Phase C/D analysis.

The implementation uses the standard reciprocal rank of the first relevant retrieved result. The frozen benchmark has a relevant first result for every query/system combination, producing MRR=1.0 for all four systems.

This is a benchmark property, not an implementation defect.

Consequently, MRR is saturated in this benchmark and should not be used to distinguish the retrieval systems.

## 6. Category-level behavior

The benchmark does **not** show that Hybrid dominates every category.

Observed patterns:

- **Exact keyword / identifier:** Dense and BM25 are frequently strong.
- **Acronym-heavy queries:** BM25 and Hybrid are strong because lexical overlap is highly informative.
- **Semantic paraphrase:** Hybrid and Reranker are often stronger.
- **Negation-sensitive queries:** Dense or Reranker can outperform Hybrid; lexical precision and semantic interpretation both matter.
- **Modifier-sensitive queries:** Dense/BM25 can be stronger where exact phrase content is important.
- **Multi-intent queries:** Hybrid and Reranker tend to benefit from broader candidate coverage and reordering.
- **Cross-reference / page-section evidence:** Hybrid and Reranker can improve ranking quality when multiple plausible candidates exist.

Category-level winners are mixed across the benchmark. This supports a retrieval-stack interpretation rather than a single universally dominant method.

## 7. Strongest Hybrid gains and failures

### Largest Hybrid gains over Dense by Recall@10

| Query | Recall@10 delta | nDCG@10 delta |
|---|---:|---:|
| CHA-012 | +0.333333 | +0.054678 |
| CHA-020 | +0.222222 | +0.361331 |
| CHA-007 | +0.200000 | +0.115034 |
| CHA-008 | +0.200000 | +0.045867 |
| CHA-023 | +0.166667 | +0.266618 |

Notable cases:

- CHA-012: Recall@10 improved from 0.50 to 0.8333.
- CHA-020: nDCG@10 improved from 0.4521 to 0.8134.

### Largest Hybrid failures vs Dense

| Query | Recall@10 delta | nDCG@10 delta |
|---|---:|---:|
| CHA-019 | -0.111111 | +0.129755 |
| CHA-021 | -0.076923 | -0.023508 |
| CHA-018 | -0.071429 | -0.060651 |
| CHA-036 | -0.047619 | -0.039313 |
| CHA-001 | -0.040000 | -0.110040 |
| CHA-005 | 0.000000 | -0.292460 |
| CHA-011 | 0.000000 | -0.104158 |

The largest ranking-quality failure is CHA-005, where Hybrid nDCG@10 drops by 0.292460 versus Dense.

## 8. Reranker behavior

Reranking produces substantial query-level gains in some cases but also substantial regressions.

Largest nDCG@10 gains over Dense include:

- CHA-020: +0.478643
- CHA-019: +0.279948
- CHA-023: +0.245903
- CHA-033: +0.234942
- CHA-003: +0.231591

Largest regressions include:

- CHA-015: -0.206453
- CHA-021: -0.200287
- CHA-037: -0.166961
- CHA-031: -0.115793
- CHA-010: -0.106324

The aggregate result therefore does not justify the blanket claim that the reranker is the best system. Its main value is rank refinement for selected candidate sets, at substantial latency cost.

## 9. Query-level winner distribution

Across the 50 frozen queries:

| Metric | Dense | BM25 | Hybrid | Reranker |
|---|---:|---:|---:|---:|
| Best Recall@5 | 34 | 10 | 3 | 3 |
| Best Recall@10 | 22 | 10 | 13 | 5 |
| Best nDCG@10 | 9 | 9 | 15 | 17 |

This shows a clear change in behavior with retrieval depth:

- Dense dominates many top-5 recall cases.
- Hybrid becomes more competitive and wins more cases at Recall@10.
- Reranker is strongest most often for nDCG@10, reflecting ranking refinement rather than candidate discovery.

## 10. Headline-claim audit

### Claim under review

> Hybrid retrieval improves retrieval quality over dense retrieval.

### Verdict

**Directionally supported, but only with a qualified formulation.**

Hybrid improves Dense on all aggregate ranking-quality metrics measured here except saturated MRR:

- Recall@5: +0.004090
- Recall@10: +0.048679
- nDCG@5: +0.024133
- nDCG@10: +0.048904

However, only Recall@10 and nDCG@10 have 95% paired bootstrap intervals that exclude zero.

### Evidence-backed formulation

> **On the frozen CHA benchmark, Hybrid retrieval improves deeper retrieval quality over Dense, with statistically supported gains in Recall@10 (+9.9%) and nDCG@10 (+7.0%). The top-5 Recall improvement is small and not statistically significant, while MRR is saturated at 1.0 across systems.**

This is the preferred research claim for the README, technical report, portfolio, and interviews.

## 11. Audit status

- [x] Frozen benchmark used as source of truth
- [x] 50-query benchmark analyzed
- [x] Aggregate Dense/BM25/Hybrid/Reranker metrics reviewed
- [x] Dense → Hybrid deltas calculated
- [x] Paired bootstrap confidence intervals reviewed
- [x] MRR implementation independently audited
- [x] Category-level behavior reviewed
- [x] Query-level winner/failure patterns reviewed
- [x] Reranker quality/latency trade-off reviewed
- [x] Headline research claim qualified
- [x] No frozen benchmark data modified
- [x] No retrieval implementation modified

**Audit conclusion:** Phase C/D retrieval analysis is complete for the current frozen benchmark. Future retrieval changes should be evaluated against this frozen baseline rather than silently replacing it.
