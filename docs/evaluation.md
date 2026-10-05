# Evaluation Methodology

Enterprise RAG treats retrieval, generation, citation quality, and faithfulness as separate evaluation dimensions.

This document defines the evaluation contract for the project. It intentionally does **not** report benchmark numbers until a fixed evaluation set and controlled run have been completed.

## 1. Evaluation layers

### Retrieval

Retrieval answers:

> Did the system retrieve the evidence needed to answer the query?

Primary metrics:

| Metric | Purpose |
|---|---|
| Recall@1 | Relevant evidence in the first result |
| Recall@5 | Relevant evidence in the top five |
| Recall@10 | Relevant evidence in the top ten |
| MRR | Rank of the first relevant result |
| nDCG@5 | Graded ranking quality in the top five |
| nDCG@10 | Graded ranking quality in the top ten |
| Precision@5 | Proportion of relevant results in the top five |
| Latency | Retrieval and ranking cost |

Retrieval comparisons should use the same corpus, queries, relevance judgments, and evaluation procedure.

### Generation

Generation answers:

> Does the response address the information need correctly?

Generation evaluation should be reported separately from retrieval performance. A strong retrieval result does not guarantee a correct generated answer.

### Citation

Citation evaluation answers:

> Does each citation resolve to a real source, and does that source support the associated claim?

Track at least:

- Citation validity
- Citation accuracy
- Citation coverage
- Invalid citation rate

### Faithfulness

Faithfulness answers:

> Are the generated claims supported by the supplied evidence?

For claim-level evaluation, report:

- Total claims
- Supported claims
- Unsupported claims
- Faithfulness rate

## 2. Golden evaluation set

The benchmark should use a fixed, versioned evaluation set derived from the actual project corpus.

Each query should have:

- Stable query ID
- Query text
- Answerability label
- Human-verified relevant chunks
- Optional graded relevance judgments
- Reference answer where appropriate
- Query category

Example JSONL record:

```json
{
  "query_id": "Q001",
  "query": "Example question",
  "answerable": true,
  "gold_chunks": [
    "document-p001-c002"
  ],
  "relevance": {
    "document-p001-c002": 3
  }
}
```

The benchmark must not be populated with invented relevance labels or fabricated results.

## 3. Baselines and ablations

The controlled retrieval comparison should include:

1. Dense retrieval
2. BM25 retrieval
3. Dense + BM25 hybrid fusion
4. Hybrid + cross-encoder reranking

Where possible, hold constant:

- Corpus
- Chunking
- Embedding model
- Query set
- Top-k evaluation
- Relevance judgments
- Hardware/runtime conditions

The goal is to measure the contribution of each retrieval component rather than assume that additional stages always improve quality.

## 4. Negative / unanswerable queries

The evaluation set should contain queries whose answer is not present in the corpus.

Expected behavior:

- The system identifies insufficient evidence.
- The answer does not fabricate unsupported facts.
- Citations do not point to unrelated evidence as if it were authoritative.

Negative cases should be reported separately from ordinary retrieval accuracy.

## 5. Error analysis

Every failed retrieval should be assigned a primary failure category where practical:

- Lexical mismatch
- Semantic mismatch
- Identifier/entity mismatch
- Acronym mismatch
- Chunk-boundary failure
- Metadata/filtering failure
- Multi-hop failure
- Corpus coverage failure

A useful error-analysis record contains the query, expected evidence, retrieved evidence, pipeline configuration, and failure diagnosis.

## 6. Reproducibility

A benchmark result should be reproducible from a documented:

```text
Corpus
  + Evaluation Set
  + Relevance Judgments
  + Pipeline Configuration
  + Model Versions
  + Top-K Settings
  + Runtime Conditions
  = Benchmark Result
```

Development-run observations must not be presented as controlled benchmark results.

## 7. Result reporting

Final reports should contain both aggregate metrics and failure analysis.

Recommended comparison table:

| Configuration | R@5 | R@10 | MRR | nDCG@5 | P95 Latency |
|---|---:|---:|---:|---:|---:|
| Dense | — | — | — | — | — |
| BM25 | — | — | — | — | — |
| Hybrid | — | — | — | — | — |
| Hybrid + Reranker | — | — | — | — | — |

Dashes are intentional until the controlled benchmark has been run.

## 8. Evaluation principle

> **Measure retrieval before optimizing generation.**

The project should use evaluation results to justify architectural changes rather than changing retrieval components first and measuring afterward.
