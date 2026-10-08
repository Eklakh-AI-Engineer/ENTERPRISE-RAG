# Evaluation data

## Frozen gold benchmark

- golden_queries_v1.json — 50 corpus-derived queries; frozen human relevance benchmark.
- human_labels_v1.json — compact immutable human relevance labels.
- results/golden_v1.json — Dense/BM25/Hybrid/Reranker results with bootstrap CIs.

## Held-out challenge benchmark

- challenge_queries_v1.json — 20 independently authored queries kept outside the frozen gold benchmark.
- 10 hard in-domain queries require human answerability/relevance adjudication before scoring.
- 10 external queries are deliberately unanswerable controls.
- scripts/evaluate_answerability.py reports insufficient-evidence and false-abstention rates from captured system responses.

## Faithfulness validation

- faithfulness_human_subset.schema.json — contract for an independent human-vs-judge subset.
- scripts/evaluate_faithfulness_judge.py — reports confusion matrix, F1 and Cohen's kappa.
- No human-validation result is published until real independent labels are supplied.
