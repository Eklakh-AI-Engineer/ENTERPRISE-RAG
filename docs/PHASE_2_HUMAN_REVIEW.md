# Phase 2 — Silver Labels → Human Review

## Purpose

The CHA Phase 2 pool is the real Dense(query) UNION BM25(query) candidate set.
This workflow creates silver AI relevance judgments first, then lets a human
review and correct them.

Silver labels are never represented as human ground truth.

## Relevance scale

- 0 — Not relevant: does not help answer the query.
- 1 — Marginal: related topic but little useful evidence.
- 2 — Relevant: useful evidence, but incomplete or indirect.
- 3 — Highly relevant: direct, specific evidence that can answer or strongly support the query.

Judge each candidate independently. Keyword overlap alone is not sufficient.

## Generate silver labels

The GitHub Actions workflow defaults to the OpenRouter free routing model:

    openrouter/free

You can override it when manually dispatching the workflow. For local runs,
set `OPENROUTER_MODEL=openrouter/free` or another available model.

Set the OpenRouter credentials in the environment:

    export OPENROUTER_API_KEY=...
    export OPENROUTER_MODEL=...

Then run:

    python scripts/label_phase2_silver.py \
      --pool data/evaluation/cha_pool_v1.json \
      --output data/evaluation/cha_silver_labels_v1.json

The script is resumable and writes after every completed query.

## Human review

Review the generated labels before treating the dataset as a human-reviewed
benchmark. Change labels where the evidence does not match the 0–3 definitions.

Prioritize:

1. low-confidence judgments;
2. labels 1 vs 2 and 2 vs 3;
3. candidates where Dense and BM25 disagree;
4. obvious topic/keyword false positives.

Keep the original silver label and record the human final label separately.

Example:

    {
      "relevance_silver": 2,
      "relevance_final": 1,
      "final_source": "human_corrected"
    }

A confirmed label:

    {
      "relevance_silver": 3,
      "relevance_final": 3,
      "final_source": "human_confirmed"
    }

## Integrity rule

Do not rename silver_ai labels to human.

The final benchmark can only be described as human-reviewed to the extent that
a person actually reviewed or confirmed those judgments.

After review, run the normal Phase 2 benchmark validator and Dense-vs-Hybrid
experiment using the final relevance field.
