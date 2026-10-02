from __future__ import annotations

import argparse
import json

from app.ingestion.factory import build_worker
from app.integrations.supabase import create_service_client


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process one pending Enterprise RAG ingestion job."
    )
    parser.add_argument("--organization-id", required=True)
    args = parser.parse_args()

    worker = build_worker(
        create_service_client(),
        organization_id=args.organization_id,
    )
    result = worker.run_once(organization_id=args.organization_id)

    if result is None:
        print(json.dumps({"status": "idle", "message": "No eligible ingestion job."}))
        return 0

    print(
        json.dumps(
            {
                "status": result.status,
                "job_id": result.id,
                "document_id": result.document_id,
                "organization_id": result.organization_id,
                "attempt_count": result.attempt_count,
                "last_error": result.last_error,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
