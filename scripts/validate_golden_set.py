#!/usr/bin/env python3
"""Validate the Enterprise RAG golden-set contract."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "benchmark",
        nargs="?",
        default="data/evaluation/golden_queries_v1.json",
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    queries = payload.get("queries", [])

    if not 50 <= len(queries) <= 100:
        raise SystemExit(f"Expected 50-100 queries; found {len(queries)}.")

    ids = [q.get("query_id") for q in queries]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise SystemExit("query_id values must be present and unique.")

    categories = Counter(q.get("category") for q in queries)
    if len(categories) < 10:
        raise SystemExit(f"Expected at least 10 categories; found {len(categories)}.")

    missing_labels = [q["query_id"] for q in queries if not q.get("relevance")]

    if payload.get("status") != "frozen":
        print("STATUS: draft_pending_human_annotation")
        print(f"Queries ready: {len(queries)}")
        print(f"Queries still missing gold labels: {len(missing_labels)}")
        print("No benchmark result is valid until the dataset is frozen.")
        return

    if missing_labels:
        raise SystemExit(
            "Frozen benchmark contains queries without relevance judgments: "
            + ", ".join(missing_labels)
        )

    for q in queries:
        for label in q["relevance"]:
            required = ("document_id", "page", "start_char", "end_char", "relevance")
            missing = [key for key in required if key not in label]
            if missing:
                raise SystemExit(f"{q['query_id']}: missing {missing}")
            if not 0 <= int(label["relevance"]) <= 3:
                raise SystemExit(f"{q['query_id']}: relevance must be 0-3")
            if int(label["page"]) < 1:
                raise SystemExit(f"{q['query_id']}: page must be >= 1")
            if int(label["end_char"]) <= int(label["start_char"]):
                raise SystemExit(f"{q['query_id']}: invalid evidence span")

    print(json.dumps({
        "valid": True,
        "status": "frozen",
        "queries": len(queries),
        "categories": dict(categories),
    }, indent=2))


if __name__ == "__main__":
    main()
