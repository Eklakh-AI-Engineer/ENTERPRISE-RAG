# Phase 0 — Baseline Freeze

**Project:** Enterprise RAG / AI Search  
**Baseline commit:** `f91ecff3a1a2d430e83ba2fafa3b40d72b2f3a8f`  
**Date:** 2026-10-01

## Purpose

Freeze the current working implementation before repository hardening and the production Vercel + Supabase migration.

Phase 0 does not change retrieval, generation, API, or frontend behavior.

## Frozen pipeline

```
Query
  ↓
Dense + BM25 retrieval
  ↓
Hybrid fusion
  ↓
Cross-encoder reranking
  ↓
Context assembly
  ↓
Evidence-constrained LLM generation
  ↓
Citation mapping / validation
  ↓
Faithfulness verification
  ↓
Evaluation + observability
```

## Frozen capabilities

- Dense semantic retrieval
- BM25 lexical retrieval
- Hybrid retrieval
- Cross-encoder reranking
- Context construction
- Evidence-constrained generation
- Citation extraction and source mapping
- Citation validation
- Claim-level faithfulness verification
- Pipeline latency/quality metrics
- FastAPI query interface
- React inspection frontend

## Baseline limitations

These remain intentionally unchanged and become later-phase work:

- Controlled labeled retrieval dataset is not yet frozen.
- Recall@5 / MRR / nDCG benchmark results are not yet established.
- Dense-vs-Hybrid controlled experiment is not yet completed.
- Query rewriting is not yet implemented.
- OCR/scanned-document coverage is incomplete.
- Token/cost measurement is not yet systematic.
- Retrieval indexes are currently local.
- Authentication, authorization, multi-user isolation, and RLS are not implemented.
- Production deployment architecture has not yet been introduced.

## Baseline rule

Future phases must preserve this implementation as the reference point. Any regression in retrieval, citation, faithfulness, or API behavior should be compared against this baseline.

## Next

**Phase 1 — Repository cleanup and reproducibility.**
