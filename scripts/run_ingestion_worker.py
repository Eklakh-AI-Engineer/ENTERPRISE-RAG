from __future__ import annotations

import argparse
import json
import time

from app.ingestion.factory import build_worker
from app.integrations.supabase import create_service_client


def process_once(worker, organization_id: str) -> bool:
    result = worker.run_once(organization_id=organization_id)
    if result is None:
        print(json.dumps({"status": "idle", "message": "No eligible ingestion job."}), flush=True)
        return False

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
        ),
        flush=True,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process Enterprise RAG ingestion jobs."
    )
    parser.add_argument("--organization-id", required=True)
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep polling for jobs instead of exiting after one attempt.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=10.0,
        help="Seconds to wait between idle polls.",
    )
    args = parser.parse_args()

    worker = build_worker(
        create_service_client(),
        organization_id=args.organization_id,
    )

    if not args.loop:
        process_once(worker, args.organization_id)
        return 0

    while True:
        processed = process_once(worker, args.organization_id)
        if not processed:
            time.sleep(max(args.poll_seconds, 1.0))


if __name__ == "__main__":
    raise SystemExit(main())
