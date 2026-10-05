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

    python scripts/validate_phase2_benchmark.py <frozen-benchmark.json>

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


## CHA corpus v1

The first real benchmark corpus is the four-document CHA policy set registered in
`data/evaluation/cha_corpus_manifest.json`.

Build the span-aware corpus locally:

    python scripts/build_corpus.py \
      --input-dir data/raw/cha \
      --output data/processed/cha_chunks.json

The corpus contains 50 candidate evaluation queries in
`data/evaluation/cha_queries_v1.json`, five per category across ten categories.

These queries are intentionally not yet a benchmark. The next required step is
to build the Dense ∪ BM25 pool and have a human label the pooled candidates with
relevance 0–3. Do not convert the query set into a benchmark until those
judgments are frozen.


## Golden benchmark v1

```text
data/evaluation/golden_queries_v1.json
data/evaluation/golden_queries_v1.schema.json
```

The repository now contains 50 corpus-derived CHA queries, distributed across 10 categories. The file is intentionally marked `draft_pending_human_annotation`.

**This is deliberate.** The existing `cha_silver_labels_v1.json` contains AI-generated silver labels, not human gold labels. It must not be promoted to gold merely to produce benchmark numbers.

### Human annotation gate

For each query:

1. Run the Dense ∪ BM25 pool against the frozen CHA corpus.
2. Review the pooled candidates.
3. Label each candidate 0–3:
   - 0 — not relevant
   - 1 — marginal/background
   - 2 — relevant evidence
   - 3 — highly relevant/directly answers
4. Record durable `document_id`, `page`, `start_char`, and `end_char`.
5. Set `answerable` to true/false.
6. Change `status` to `frozen` only after the full set has been reviewed.

Validate the dataset:

```bash
python scripts/validate_golden_set.py
```

The validator permits the draft state so the repository can track progress, but the benchmark runner refuses to execute until the dataset is frozen and every query has relevance judgments.

### Benchmark runner

After human annotation is frozen:

```bash
python scripts/run_golden_retrieval_benchmark.py \
  --benchmark data/evaluation/golden_queries_v1.json \
  --chunks data/processed/cha_chunks.json \
  --systems dense bm25 hybrid reranker \
  --top-k 10 \
  --candidate-k 20 \
  --output data/evaluation/results/golden_v1.json
```

The runner reports query-level and aggregate:

- Recall@5 / Recall@10
- MRR
- nDCG@5 / nDCG@10
- Retrieval latency
- Category-level slices
- Paired Hybrid-vs-Dense deltas
- Bootstrap confidence intervals

No LLM generation call is required for the retrieval benchmark.

### Why the human gate matters

Retrieval metrics require labeled relevant evidence. A gold set should therefore be a fixed, curated evaluation artifact rather than an unverified model-generated label file. The benchmark is designed to keep retrieval evaluation separate from generation evaluation, so a retrieval regression cannot be hidden by a strong generator.
