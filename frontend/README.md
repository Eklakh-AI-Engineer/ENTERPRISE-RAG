# Enterprise RAG Frontend

React + Vite inspection frontend for the Enterprise RAG pipeline.

## Purpose

The frontend is a development and inspection surface for:

- querying the local RAG pipeline;
- inspecting retrieved evidence;
- viewing citations;
- viewing pipeline/evaluation telemetry.

It is not currently presented as the production deployment surface.

## Development

    cd frontend
    npm ci
    npm run dev

Default development server:

    http://localhost:5173

## Validation

    npm run lint
    npm run build

## Configuration

The frontend can point to another API host through Vite environment configuration. Do not put provider secrets or server-side API keys in VITE_* variables.

See [../docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md) for the complete local workflow.
