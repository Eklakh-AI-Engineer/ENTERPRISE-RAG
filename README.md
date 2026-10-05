# Enterprise RAG / AI Search

> **Retrieval engineering for evidence-grounded LLM systems.** Dense + BM25 retrieval, RRF fusion, cross-encoder reranking, citation traceability, faithfulness verification, and reproducible evaluation.

Enterprise RAG is built around a simple principle:

> **Retrieve the evidence. Rank it. Cite it. Verify it. Measure it.**

This repository is more than a PDF chatbot. Retrieval, generation, citations, evaluation, persistence, and observability are separated so each layer can be tested and improved independently.

## Project status

**Current milestone: local-first retrieval engineering + benchmark completion.**

| Area | Status |
|---|---|
| Dense retrieval | Implemented |
| BM25 retrieval | Implemented locally |
| Hybrid / RRF | Implemented locally |
| Cross-encoder reranking | Implemented |
| Evidence-constrained generation | Implemented |
| Citation mapping / validation | Implemented |
| Faithfulness verification | Implemented |
| Evaluation harness | Implemented |
| 50-query corpus-derived benchmark draft | Ready for annotation |
| Human-verified gold labels | Pending |
| Controlled retrieval results | Pending |
| Production multi-tenant release | Later milestone |

> **Integrity rule:** development observations are not benchmark results. No controlled metric is published until the evaluation corpus, relevance judgments, configuration, and run are frozen.

## Architecture

```text
                         User Query
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
       Dense Retrieval                  BM25 Retrieval
              │                             │
              └──────────────┬──────────────┘
                             ▼
                       RRF / Hybrid Fusion
                             │
                             ▼
                  Cross-Encoder Reranking
                             │
                             ▼
                     Context Assembly
                  document / page / chunk
                             │
                             ▼
                Evidence-Constrained LLM
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
         Citation Mapping          Faithfulness Check
                │                         │
                └────────────┬────────────┘
                             ▼
                    Evaluation + Metrics
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the implemented design and later production boundary.

## What is engineered here?

### Retrieval
- Dense semantic retrieval with SentenceTransformers
- BM25 lexical retrieval for exact terms, identifiers, acronyms, and terminology
- Hybrid candidate fusion using RRF
- Configurable candidate and top-k selection
- Cross-encoder reranking

### Evidence and generation
- Context assembly preserves document/page/chunk provenance
- Evidence-constrained generation through an OpenRouter-backed provider interface
- Explicit insufficient-evidence behavior
- Strict [Source N] citation mapping
- Citation validity and citation accuracy treated as separate concepts
- Claim-level faithfulness verification

### Evaluation

    Retrieval quality
          ≠
    Generation quality
          ≠
    Citation quality
          ≠
    Faithfulness

The active CHA benchmark contains **50 corpus-derived queries across 10 categories**. It is currently a draft pending human relevance annotation. See [docs/EVALUATION.md](docs/EVALUATION.md).

## Repository structure

```text
ENTERPRISE-RAG/
│
├── app/                         # Backend application and domain logic
│   ├── api/                     # FastAPI routes and request boundaries
│   ├── parsing/                 # PDF extraction and OCR fallback
│   ├── chunking/                # Chunking + durable evidence spans
│   ├── ingestion/               # Document ingestion orchestration
│   ├── indexing/                # Index construction / persistence
│   ├── retrieval/               # Dense, BM25, hybrid retrieval
│   ├── reranking/               # Cross-encoder ranking
│   ├── generation/              # LLM provider + grounded generation
│   ├── citations/               # Citation extraction and mapping
│   ├── faithfulness/            # Claim/evidence verification
│   ├── evaluation/              # Evaluation primitives
│   ├── query/                   # Query pipeline orchestration
│   └── observability/           # Pipeline telemetry
│
├── data/
│   └── evaluation/              # Versioned benchmark contracts and labels
│
├── docs/
│   ├── README.md                # Documentation map
│   ├── ARCHITECTURE.md          # Current architecture
│   ├── EVALUATION.md            # Evaluation methodology + benchmark
│   ├── PROJECT_PLAN.md          # Active delivery roadmap
│   ├── DEVELOPMENT.md           # Local development workflow
│   ├── DEPLOYMENT.md             # Later production deployment
│   ├── DATABASE.md               # Production data model
│   ├── SECURITY.md               # Security baseline
│   ├── IMPLEMENTATION_PLAN.md    # Detailed implementation plan
│   └── history/                  # Superseded audits and historical snapshots
│
├── frontend/                    # React + Vite inspection UI
├── scripts/                     # Reproducible build/evaluation utilities
├── tests/                       # Canonical automated test suite
├── screenshots/                 # Working application evidence
├── supabase/                    # Database schema/migration artifacts
│
├── .env.example                 # Environment configuration template
├── Dockerfile                   # Backend container
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Test configuration
└── README.md                    # Project entry point
```

## Documentation map

| Document | Purpose |
|---|---|
| [Documentation index](docs/README.md) | Find the right document quickly |
| [Architecture](docs/ARCHITECTURE.md) | Implemented pipeline and production boundary |
| [Evaluation](docs/EVALUATION.md) | Metrics, benchmark contract, annotation gate |
| [Project plan](docs/PROJECT_PLAN.md) | Current roadmap and definition of done |
| [Development](docs/DEVELOPMENT.md) | Setup, tests, local execution |
| [Deployment](docs/DEPLOYMENT.md) | Production prerequisites and sequence |
| [Database](docs/DATABASE.md) | Persistence model and pgvector parity gate |
| [Security](docs/SECURITY.md) | Secrets, tenant isolation, request-path controls |
| [Evaluation data](data/evaluation/README.md) | Benchmark data contract |
| [History](docs/history/README.md) | Previous audits and resume snapshots |

## Evaluation workflow

```text
Frozen corpus
    ↓
50 corpus-derived queries
    ↓
Dense ∪ BM25 candidate pool
    ↓
Human relevance labels (0–3)
    ↓
Frozen benchmark
    ↓
Dense / BM25 / Hybrid / Reranker
    ↓
Recall / MRR / nDCG / latency
    ↓
Failure analysis
```

Validate:

    python scripts/validate_golden_set.py

After human annotation is frozen:

    python scripts/run_golden_retrieval_benchmark.py       --benchmark data/evaluation/golden_queries_v1.json       --chunks data/processed/cha_chunks.json       --systems dense bm25 hybrid reranker       --top-k 10       --candidate-k 20       --output data/evaluation/results/golden_v1.json

## Local development

### Backend

    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/macOS
    # source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.api.main:app --reload

### Frontend

    cd frontend
    npm ci
    npm run dev

### Tests

    pytest -q
    python -m compileall app tests

Frontend validation:

    cd frontend
    npm ci
    npm run lint
    npm run build

## Screenshots

The repository includes working-run evidence of the application interface, backend/frontend startup, grounded query response, citation/evaluation output, and retrieval observability.

Screenshots are implementation evidence, **not controlled benchmark evidence**.

## Engineering principles

1. **Measure retrieval independently.**
2. **Preserve durable evidence provenance.**
3. **Keep retrieval and generation separable.**
4. **Treat citations as evidence links, not decoration.**
5. **Validate faithfulness separately from retrieval relevance.**
6. **Optimize only after measurement.**
7. **Never convert model-generated labels into human ground truth.**

## Roadmap

1. Complete human annotation of the 50-query CHA pool.
2. Freeze the benchmark and configuration.
3. Run Dense, BM25, Hybrid/RRF, and reranker comparisons.
4. Perform query-level failure analysis.
5. Validate the faithfulness judge against a human subset.
6. Freeze the local evidence-grounded product.
7. Re-enter the production deployment track only after the local gates pass.

## Author

**Eklakh Dewan** — B.Tech, Artificial Intelligence & Data Science

[GitHub repository](https://github.com/Eklakh-AI-Engineer/ENTERPRISE-RAG)
