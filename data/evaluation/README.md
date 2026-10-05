# Evaluation Data

This directory contains versioned evaluation contracts, query sets, relevance judgments, corpus manifests, and benchmark outputs.

## Benchmark contract

The production-quality retrieval benchmark must contain **50–100 queries** derived from the fixed project corpus.

Current benchmark draft:

- Corpus: CHA-POLICY-CORPUS-V1
- Queries: 50
- Categories: 10
- Status: draft_pending_human_annotation

The draft is intentionally incomplete until human relevance judgments are frozen.

## Evidence judgments

Each candidate judgment uses durable provenance:

- document_id
- page
- start_char
- end_char
- graded relevance 0–3

| Label | Meaning |
|---:|---|
| 0 | Not relevant |
| 1 | Marginal/background |
| 2 | Relevant evidence |
| 3 | Highly relevant / directly answers |

## Pool construction

For every query:

    Dense(query) ∪ BM25(query)

The annotator reviews the pooled candidates rather than allowing one retrieval method to define the relevance set.

## Versioning rules

Increment the benchmark version when corpus documents, evidence spans, query definitions, relevance judgments, or preprocessing materially change.

Record model and retrieval configuration versions separately.

## Available artifacts

| Artifact | Purpose |
|---|---|
| cha_corpus_manifest.json | Frozen corpus identity and hashes |
| cha_queries_v1.json | Corpus-derived candidate query set |
| golden_queries_v1.json | Benchmark-shaped 50-query draft |
| golden_queries_v1.schema.json | Validation schema |
| cha_silver_labels_v1.json | Model-generated silver checkpoint; not gold |
| results/ | Controlled benchmark outputs when generated |

## Validation

    python scripts/validate_golden_set.py

## Benchmark

After human annotation is frozen:

    python scripts/run_golden_retrieval_benchmark.py \
      --benchmark data/evaluation/golden_queries_v1.json \
      --chunks data/processed/cha_chunks.json \
      --systems dense bm25 hybrid reranker \
      --top-k 10 \
      --candidate-k 20 \
      --output data/evaluation/results/golden_v1.json

Do not publish benchmark numbers until the benchmark status is frozen.
