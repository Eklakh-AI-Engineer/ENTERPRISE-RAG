# Architecture

Enterprise RAG is structured as a modular retrieval and evidence-grounding pipeline.

## Request path

```text
User Query
    |
    v
Dense Retrieval --------                         > Hybrid Fusion
BM25 Retrieval --------/
    |
    v
Cross-Encoder Reranking
    |
    v
Context Assembly
(document / page / chunk metadata)
    |
    v
Evidence-Constrained Generation
    |
    +----------------------+
    |                      |
    v                      v
Citation Mapping     Faithfulness Verification
    |                      |
    +----------+-----------+
               v
        Pipeline Metrics
```

## Retrieval layer

The retrieval layer deliberately exposes multiple signals:

- **Dense retrieval** captures semantic similarity.
- **BM25** captures lexical overlap, terminology, identifiers, and exact phrases.
- **Hybrid retrieval** combines the candidate sets/rankings.
- **Cross-encoder reranking** reorders the candidate evidence using query-document interaction.

The components are kept separate so each stage can be evaluated independently.

## Context assembly

Retrieved chunks retain source metadata such as:

- Document identity
- Page
- Chunk identity
- Source content

This metadata is carried into generation and later citation resolution.

## Generation

The generation layer uses an OpenRouter-backed provider interface and an evidence-constrained prompt.

The intended behavior is:

1. Generate from supplied evidence.
2. Use the project's citation format.
3. Avoid claiming unsupported information.
4. Indicate insufficient evidence when the corpus cannot support an answer.

## Citation mapping

Citations are represented as source references in the generated answer.

The mapping flow is:

```text
[Source N]
   |
   v
Retrieved context entry
   |
   v
Document / page / chunk metadata
```

Citation validity and citation accuracy are separate concepts:

- **Validity:** the citation identifier resolves to a real retrieved source.
- **Accuracy:** the resolved evidence actually supports the associated claim.

## Faithfulness verification

Faithfulness verification operates after generation and citation mapping.

Conceptually:

```text
Generated claim
      |
      v
Referenced evidence
      |
      v
Evidence verification
      |
   +--+--+
   |     |
Supported Unsupported
```

The verifier is intended to judge the supplied evidence rather than introduce outside knowledge.

## Observability

The pipeline records stage-level and end-to-end measurements, including retrieval, reranking, generation, citation verification, faithfulness verification, counts, and evaluation signals.

These measurements should be used to identify bottlenecks before optimization.

## Design principles

### Retrieval is measurable

Retrieval quality is evaluated independently from the final LLM response.

### Evidence is first-class

Source metadata is preserved throughout the pipeline so answers can be traced back to document evidence.

### Components remain replaceable

Dense retrieval, BM25, hybrid fusion, reranking, generation, citation mapping, and evaluation are separate pipeline components.

### Optimize after measurement

Changes to models, chunking, ranking, or prompts should be justified by benchmark or error-analysis evidence.

## Evaluation boundary

This architecture document describes the implemented pipeline shape. It does not imply that every planned benchmark or production capability has already been completed. Controlled results belong in the evaluation reports.
