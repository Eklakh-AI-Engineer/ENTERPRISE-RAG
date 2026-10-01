# Phase 2 benchmark data

This directory contains the versioned evaluation contract for the controlled retrieval experiment.

## Required benchmark

The production-quality Phase 2 benchmark must contain **50–100 queries** distributed across the project's evaluation categories.

Do not manufacture labels to fill the quota. Relevance judgments must come from the fixed corpus and the Dense ∪ BM25 candidate pool.

## Evidence labels

Each judgment is durable across chunker changes:

- document_id
- page
- start_char
- end_char
- graded relevance from 0 to 3

Suggested grading:

| Relevance | Meaning |
|---:|---|
| 0 | Not relevant |
| 1 | Marginal/background relevance |
| 2 | Relevant evidence |
| 3 | Highly relevant / directly answers the query |

## Pool construction

For every query, retrieve the candidate union Dense(query) ∪ BM25(query) using the same corpus and query text.

The annotator then judges the pooled candidates. This prevents the relevance set from being defined by one retrieval method.

## Versioning

Increment benchmark_version whenever corpus documents, evidence spans, or relevance judgments materially change, or preprocessing changes the evidence mapping.

Record model/configuration versions separately so experiments remain reproducible.

## Required reporting

Report query-level and aggregate Recall@5, Recall@10, MRR, nDCG@5, nDCG@10, retrieval latency, candidate count, and reranking latency where applicable.

For Dense-vs-Hybrid, report paired treatment-minus-baseline deltas and bootstrap confidence intervals.

A point estimate alone is not sufficient evidence for a retrieval improvement.