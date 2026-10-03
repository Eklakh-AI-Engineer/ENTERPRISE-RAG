# Enterprise RAG — Production Deployment (Later Stage)

Production deployment is intentionally **not the current development gate**. The active milestone is the local retrieval-engineering product described in [PROJECT_PLAN.md](PROJECT_PLAN.md).

When the local benchmark and product are frozen, the production topology is:

```
React/Vite
   ↓
Vercel
   ↓ HTTPS + authenticated user context
FastAPI + ML inference
   ↓
Supabase Auth / Postgres / pgvector / Storage
   ↑
Long-running ingestion worker
```

## Production prerequisites

Before deployment begins:

- [ ] Local PDF → chunk → retrieval → reranking → generation → citation → faithfulness flow is frozen.
- [ ] 50–100 human-verified evaluation queries are frozen.
- [ ] Dense/BM25/Hybrid/RRF benchmark is reproducible.
- [ ] Reranking and query-rewriting experiments are documented.
- [ ] Latency and token/cost measurements are recorded.
- [ ] Production persistence has a verified migration plan.
- [ ] Auth/RLS cross-tenant tests pass.
- [ ] Ingestion worker reliability is verified.

## Production sequence

1. Reconcile the production Supabase schema with the frozen local data model.
2. Verify pgvector retrieval parity against the local Dense baseline.
3. Verify private Storage upload/read/delete behavior.
4. Verify authenticated API request propagation and RLS.
5. Harden the ingestion worker for multi-tenant operation and lease recovery.
6. Deploy FastAPI to a long-running container service.
7. Deploy the React/Vite frontend.
8. Configure CORS and HTTPS.
9. Run an authenticated upload → ingestion → query E2E test.
10. Run negative cross-tenant authorization tests.
11. Add production rate limits, quotas, structured logs, and monitoring.

## Important

The previous Railway-specific deployment files and production smoke script were removed from the active repository during the local-first cleanup. Their implementation history remains in Git. Production deployment should be rebuilt from the frozen local contract rather than becoming a second moving target during research.

Never commit provider secrets or expose server-side keys through `VITE_*` variables.
