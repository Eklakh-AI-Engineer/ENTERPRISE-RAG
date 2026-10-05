# Enterprise RAG — Evaluation

**Status:** Active evaluation contract  
**Last reviewed:** 2026-10-05

This document defines how retrieval, generation, citations, and faithfulness are evaluated. It intentionally does not publish benchmark numbers until the evaluation set and relevance judgments are frozen.

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
    draft_pending_human_annotation

This is a benchmark **draft**, not human gold.

The existing cha_silver_labels_v1.json contains model-generated silver judgments. It must not be represented as human ground truth.

### Human annotation gate

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
6. Change the benchmark status to frozen only after the full set has been reviewed.

Validate:

    python scripts/validate_golden_set.py

The validator permits the draft state for progress tracking. The benchmark runner refuses to execute until the set is frozen and every query has relevance judgments.

## 3. Controlled retrieval comparison

Run the same corpus, queries, relevance judgments, chunking, and evaluation procedure for:

1. Dense
2. BM25
3. Hybrid/RRF
4. Hybrid/RRF + Cross-Encoder

Runner:

    python scripts/run_golden_retrieval_benchmark.py       --benchmark data/evaluation/golden_queries_v1.json       --chunks data/processed/cha_chunks.json       --systems dense bm25 hybrid reranker       --top-k 10       --candidate-k 20       --output data/evaluation/results/golden_v1.json

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

## 5. Negative / unanswerable queries

The evaluation set should include corpus-unanswerable queries.

Expected behavior:

- identify insufficient evidence;
- avoid unsupported factual claims;
- avoid citing unrelated evidence as authoritative.

Negative cases should be analyzed separately from ordinary retrieval accuracy.

## 6. Error analysis

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

## 7. Statistical reporting

For paired Dense-vs-Hybrid comparisons, report query-level deltas and bootstrap confidence intervals.

Point estimates without query-level comparison are insufficient evidence for a retrieval improvement.

## 8. Result discipline

Do not publish:

- development-run metrics as benchmark numbers;
- AI-generated silver labels as human gold;
- a benchmark result without a frozen corpus/query/label configuration.

Change retrieval architecture **after** measurement and failure analysis, not before.
