#!/usr/bin/env python3
"""Validate the frozen Phase 2 benchmark contract before an experiment run."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark")
    args = parser.parse_args()

    payload = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    queries = payload.get("queries", [])

    if not 50 <= len(queries) <= 100:
        raise SystemExit(
            f"Expected 50–100 queries, found {len(queries)}."
        )

    ids = [item.get("query_id") for item in queries]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise SystemExit("query_id values must be present and unique.")

    categories = Counter(item.get("category") for item in queries)
    if len(categories) < 10:
        raise SystemExit(
            f"Expected at least 10 evaluation categories, found {len(categories)}."
        )

    for item in queries:
        if not item.get("query"):
            raise SystemExit(f"{item['query_id']}: query is empty.")

        relevance = item.get("relevance", [])
        if not relevance:
            raise SystemExit(f"{item['query_id']}: no relevance judgments.")

        for judgment in relevance:
            required = (
                "document_id",
                "page",
                "start_char",
                "end_char",
                "relevance",
            )
            missing = [key for key in required if key not in judgment]
            if missing:
                raise SystemExit(
                    f"{item['query_id']}: missing evidence fields {missing}."
                )

            if judgment["page"] < 1:
                raise SystemExit(f"{item['query_id']}: page must be >= 1.")
            if judgment["start_char"] < 0 or judgment["end_char"] <= judgment["start_char"]:
                raise SystemExit(
                    f"{item['query_id']}: invalid evidence span."
                )
            if not 0 <= judgment["relevance"] <= 3:
                raise SystemExit(
                    f"{item['query_id']}: relevance must be in [0, 3]."
                )

    print(json.dumps({
        "valid": True,
        "queries": len(queries),
        "categories": dict(categories),
        "benchmark_version": payload["benchmark_version"],
        "corpus": payload["corpus"],
    }, indent=2))


if __name__ == "__main__":
    main()
