# Phase 2 — Human Relevance Review

## Purpose

The CHA Phase 2 pool is the Dense(query) UNION BM25(query) candidate set.
The next evaluation gate is **human relevance labeling**. AI-generated silver
labels are not part of the active benchmark workflow.

## Relevance scale

- 0 — Not relevant: does not help answer the query.
- 1 — Marginal: related topic but little useful evidence.
- 2 — Relevant: useful evidence, but incomplete or indirect.
- 3 — Highly relevant: direct, specific evidence that can answer or strongly support the query.

Judge each candidate independently. Keyword overlap alone is not sufficient.

## Human review procedure

For each query:

1. Review every pooled candidate.
2. Assign a 0–3 relevance judgment.
3. Record the human judgment and reviewer metadata in the frozen evaluation artifact.
4. Preserve the candidate's document, page, section, and chunk identifiers.
5. Record disagreements or uncertainty for later adjudication.

Prioritize careful review of:

1. labels near the 1/2 and 2/3 boundaries;
2. candidates where Dense and BM25 disagree;
3. acronym-heavy and identifier queries;
4. negation- and modifier-sensitive queries;
5. cross-reference and metadata-filtered queries;
6. obvious topic/keyword false positives.

## Integrity rule

Do not describe an AI-generated or heuristic label as human ground truth.

The retrieval benchmark can only be described as **human-verified** to the extent
that a person actually reviewed or confirmed the relevance judgments.

## Completion gate

The Phase 2 benchmark is ready only when the frozen query set has human-verified
relevance judgments sufficient to support Recall@5, MRR, and nDCG.

After review:

- validate the final relevance artifact;
- run Dense, BM25, and Hybrid/RRF retrieval evaluation;
- run the controlled Dense-vs-Hybrid experiment;
- retain the fixed corpus, query set, relevance judgments, and evaluation procedure
  so the results are reproducible.
