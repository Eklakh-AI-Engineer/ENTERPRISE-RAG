# Enterprise RAG — Documentation

This directory contains the project's technical contracts, active plans, and historical snapshots.

## Start here

| Document | Use it for |
|---|---|
| [Architecture](ARCHITECTURE.md) | Current retrieval/evidence pipeline and production boundary |
| [Evaluation](EVALUATION.md) | Benchmark methodology, annotation gate, and metrics |
| [Project Plan](PROJECT_PLAN.md) | Current roadmap and definition of done |
| [Development](DEVELOPMENT.md) | Local setup, testing, and development rules |
| [Deployment](DEPLOYMENT.md) | Later production deployment prerequisites |
| [Database](DATABASE.md) | Persistence model, RLS boundary, pgvector parity |
| [Security](SECURITY.md) | Security baseline and tenant-isolation rules |
| [Implementation Plan](IMPLEMENTATION_PLAN.md) | Detailed implementation plan |

## Documentation conventions

- **Active contracts** use stable names such as ARCHITECTURE.md and EVALUATION.md.
- **Plans** describe intended work and are not evidence that the work is complete.
- **History** contains superseded audits and point-in-time snapshots.
- **Benchmark artifacts** live under data/evaluation/, not in narrative documentation.
- Every material evaluation change should identify its corpus, benchmark, configuration, and model versions.

## History

Historical project audits are intentionally separated from active documentation:

- [2026-10-01 audit](history/PROJECT_AUDIT_2026-10-01.md)
- [2026-10-02 audit](history/PROJECT_AUDIT_2026-10-02.md)

For the current state, use the active documents in this directory.
