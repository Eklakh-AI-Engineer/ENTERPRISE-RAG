# Enterprise RAG — Development Guide

## Prerequisites

- Python 3.12+
- Node.js compatible with the checked-in frontend lockfile
- npm
- Git
- Optional Docker

## Backend setup

Windows:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt

Linux/macOS:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Create .env from .env.example.

At minimum:

    OPENROUTER_API_KEY=...
    OPENROUTER_MODEL=...

## Backend run

    uvicorn app.api.main:app --reload

Default:
http://127.0.0.1:8000

Health:
curl http://127.0.0.1:8000/health

## Frontend setup

    cd frontend
    npm ci

Optional environment file:

    cp .env.example .env

Run:

    npm run dev

Default:
http://localhost:5173

VITE_API_BASE_URL can point the frontend at another API host.

## Tests

    pytest -q
    python -m compileall app tests

Frontend:

    cd frontend
    npm ci
    npm run lint
    npm run build

## Docker

    docker build -t enterprise-rag-api .
    docker run --rm -p 8000:8000 --env-file .env enterprise-rag-api

## Development rules

- Do not commit .env or provider keys.
- Do not commit generated FAISS indexes or model caches.
- Do not treat development-run metrics as benchmark results.
- Keep retrieval components independently testable.
- Record model/configuration changes when running evaluation experiments.
- Preserve benchmark versions when changing retrieval behavior.

A retrieval change should include a corresponding evaluation artifact once Phase 2 is active.
