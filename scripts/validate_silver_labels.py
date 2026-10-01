#!/usr/bin/env python3
"""Validate the Phase 2 silver-label artifact without changing it."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("labels", type=Path)
    parser.add_argument("--expected-queries", type=int, default=50)
    parser.add_argument("--expected-judgments", type=int, default=780)
    args = parser.parse_args()

    payload = json.loads(args.labels.read_text(encoding="utf-8"))
    queries = payload.get("queries", [])

    errors: list[str] = []

    if payload.get("schema_version") != "phase2-silver-v1":
        errors.append("unexpected schema_version")
    if payload.get("label_source") != "silver_ai":
        errors.append("label_source must be silver_ai")
    if not payload.get("model"):
        errors.append("model is missing")
    if payload.get("prompt_version") != "phase2-relevance-silver-v1":
        errors.append("unexpected prompt_version")
    if len(queries) != payload.get("completed_queries"):
        errors.append("completed_queries does not match query records")

    total = 0
    query_ids = set()

    for query in queries:
        query_id = query.get("query_id")
        if not query_id or query_id in query_ids:
            errors.append(f"duplicate/missing query_id: {query_id!r}")
        query_ids.add(query_id)

        candidate_count = int(query.get("candidate_count", -1))
        judgments = query.get("judgments", [])

        if len(judgments) != candidate_count:
            errors.append(
                f"{query_id}: expected {candidate_count} judgments, got {len(judgments)}"
            )

        indices = []
        for judgment in judgments:
            idx = judgment.get("candidate_index")
            relevance = judgment.get("relevance")
            confidence = judgment.get("confidence")

            if not isinstance(idx, int) or idx < 0 or idx >= candidate_count:
                errors.append(f"{query_id}: invalid candidate_index {idx!r}")
            indices.append(idx)

            if relevance not in {0, 1, 2, 3}:
                errors.append(f"{query_id}: invalid relevance {relevance!r}")

            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                errors.append(f"{query_id}: invalid confidence {confidence!r}")

            if judgment.get("label_source") != "silver_ai":
                errors.append(f"{query_id}: non-silver label_source")

        if len(set(indices)) != len(indices):
            errors.append(f"{query_id}: duplicate candidate_index values")

        total += len(judgments)

    if payload.get("total_queries") != args.expected_queries:
        errors.append(
            f"total_queries metadata should be {args.expected_queries}, "
            f"got {payload.get('total_queries')}"
        )

    if len(queries) not in {0, args.expected_queries}:
        errors.append(
            f"completed query count must be 0 or {args.expected_queries}, got {len(queries)}"
        )

    if len(queries) == args.expected_queries and total != args.expected_judgments:
        errors.append(
            f"complete artifact should contain {args.expected_judgments} judgments, got {total}"
        )

    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        raise SystemExit(1)

    print(
        json.dumps(
            {
                "valid": True,
                "model": payload.get("model"),
                "status": payload.get("status"),
                "completed_queries": len(queries),
                "total_queries": payload.get("total_queries"),
                "judgments": total,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
