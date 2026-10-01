# Enterprise RAG — Evaluation

## Phase 0 baseline

The frozen baseline is documented in docs/PHASE_0_BASELINE.md.

Phase 1 does not establish benchmark scores. It establishes the reproducibility and architecture needed to measure them fairly.

## Current development evaluation

The repository contains retrieval metric helpers and benchmark infrastructure.

Available retrieval metrics currently include:
- Recall@K
- Precision@K
- Hit@K
- Reciprocal Rank
- Mean Reciprocal Rank

The controlled benchmark still requires:
- fixed corpus version
- 50–100 labeled queries
- page/span-level evidence labels
- Dense ∪ BM25 relevance pooling
- graded relevance
- nDCG@5 and nDCG@10
- bootstrap confidence intervals
- paired Dense-vs-Hybrid comparisons

## Metric separation

Do not collapse all quality dimensions into one score.

Retrieval measures whether relevant evidence is retrieved and how highly it is ranked.

Citation measures whether generated [Source N] references resolve to retrieved evidence and whether citation mappings are valid.

Faithfulness measures whether generated claims are supported by the supplied evidence. The LLM judge is an evaluation instrument, not ground truth.

Answer relevance measures whether the response addresses the user's information need.

Operations measures retrieval, reranking, generation, verification, and end-to-end latency.

## Phase 2 benchmark design

Candidate pools must be built from:

    Dense(query) ∪ BM25(query)

before relevance judgments are finalized.

This avoids constructing the relevance set from only one retrieval system.

Evaluation labels should use durable:
- document identity
- page
- text span / evidence region

rather than relying only on chunk IDs.

When chunking changes, create a new benchmark version instead of silently reusing labels.

## Reproducibility record

Every published benchmark should record:
- benchmark version
- corpus/document hash
- chunker version/configuration
- embedding model/version
- reranker model/version
- retrieval top-k
- candidate-k
- RRF parameters
- random seed where applicable
- raw query-level results
- aggregation method
- bootstrap configuration
- judge model/prompt/configuration if answer evaluation is included

## Dense vs Hybrid

Keep constant:
- corpus
- query set
- relevance judgments
- chunking
- embedding model
- reranker
- evaluation code

Only retrieval strategy should change:

    Dense baseline
    vs
    Dense + BM25 + RRF

Report:
- Recall@5/10
- MRR
- nDCG@5/10
- retrieval latency
- candidate count
- reranking latency
- query-level paired deltas
- bootstrap confidence intervals

Do not claim Hybrid is better until this experiment is complete.


## Phase 2 execution commands

Validate the final benchmark before running the experiment:

    python scripts/validate_phase2_benchmark.py data/evaluation/phase2_benchmark.json

Build the unbiased annotation pool from the frozen corpus:

    python scripts/build_relevance_pool.py \
      --queries data/evaluation/phase2_queries.json

Run the controlled Dense-vs-Hybrid experiment:

    python scripts/run_dense_vs_hybrid.py \
      --benchmark data/evaluation/phase2_benchmark.json

The experiment intentionally fails when fewer than 50 or more than 100 labeled
queries are supplied. This prevents a development sample from being reported
as the Phase 2 benchmark.

## Faithfulness judge validation

Record a human-labeled subset using:

    data/evaluation/faithfulness_human_subset.example.json

Then compare the judge against human labels:

    python scripts/evaluate_faithfulness_judge.py \
      --labels data/evaluation/faithfulness_human_subset.json

The resulting accuracy, precision, recall, and F1 describe agreement with the
human subset; they do not turn the judge into ground truth.
