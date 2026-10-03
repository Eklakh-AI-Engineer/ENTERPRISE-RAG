# Enterprise RAG — Deployment

## Phase 1 deployment decision

| Component | Initial target | Reason |
|---|---|---|
| React/Vite frontend | Vercel | Static/edge-friendly UI deployment |
| FastAPI + ML inference | Long-running container service | SentenceTransformer + CrossEncoder startup/runtime cost |
| Ingestion worker | Long-running worker service | Long-running OCR/embed/index jobs |
| Auth / database / vectors / storage | Supabase | Managed application data plane |

The exact long-running host remains provider-agnostic until the resource benchmark is executed.

## Vercel feasibility benchmark

Run:

    python scripts/phase1_feasibility.py

For cached-model measurements:

    python scripts/phase1_feasibility.py --load-models

For concurrency:

    python scripts/phase1_feasibility.py --load-models --concurrency 4

Required measurements before a Vercel inference decision:
- bundle/package size
- cold start
- model initialization
- peak memory
- request duration
- concurrent behavior
- execution-time compatibility

The current architecture has a safe fallback: keep the UI on Vercel and run Python inference on a long-running container.

## Backend container

The repository includes Dockerfile and .dockerignore.

Build:

    docker build -t enterprise-rag-api .

Run:

    docker run --rm -p 8000:8000 --env-file .env enterprise-rag-api

Local retrieval indexes are intentionally excluded from the image. Production persistence and indexing move to Supabase in later phases.

## Environment

Backend:
- OPENROUTER_API_KEY
- OPENROUTER_MODEL
- DENSE_INDEX_PATH
- DENSE_METADATA_PATH
- BM25_METADATA_PATH
- DENSE_MODEL
- RERANKER_MODEL
- RETRIEVAL_TOP_K
- RERANK_TOP_K
- CANDIDATE_K
- API_HOST
- API_PORT
- CORS_ORIGINS
- ENVIRONMENT
- LOG_LEVEL
- APP_VERSION
- SUPABASE_URL
- SUPABASE_PUBLISHABLE_KEY
- SUPABASE_SERVICE_ROLE_KEY
- SUPABASE_DOCUMENTS_BUCKET
- MAX_UPLOAD_BYTES
- INGESTION_PIPELINE_VERSION

Frontend:
- VITE_API_BASE_URL

Never expose provider API keys through VITE_* variables.

## Deployment sequence

1. Build and test the frontend.
2. Build the backend container.
3. Run the Phase 1 feasibility benchmark.
4. Select the long-running inference host.
5. Configure HTTPS between frontend and API.
6. Configure JWT propagation and ensure Vercel and the API use the same Supabase project URL and publishable key.
7. Add Supabase data plane in Phase 3.
8. Add async worker in Phase 5.
9. Add production smoke tests in Phase 7.

## Current limitation

The quantitative Vercel resource benchmark has not been executed in this environment because the environment cannot access the repository's full model/runtime stack. The benchmark harness is committed so it can be executed on the actual development, CI, or deployment host.
