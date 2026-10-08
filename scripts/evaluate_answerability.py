#!/usr/bin/env python3
"""Measure abstention/insufficient-evidence behavior on unanswerable queries."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ABSTENTION_PATTERNS = (
    r"i don't have enough information",
    r"insufficient information",
    r"not enough information",
    r"cannot answer",
    r"can't answer",
    r"cannot be answered",
    r"not supported by the provided",
    r"not contained in the provided",
)


def is_insufficient_evidence(answer: str) -> bool:
    text = re.sub(r"\s+", " ", answer.lower()).strip()
    return any(re.search(pattern, text) for pattern in ABSTENTION_PATTERNS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", required=True)
    parser.add_argument("--output", default="data/evaluation/results/challenge_v1_answerability.json")
    args = parser.parse_args()

    payload = json.loads(Path(args.responses).read_text(encoding="utf-8"))
    rows = payload["responses"]
    unanswerable = [r for r in rows if r.get("expected_answerable") is False]
    answerable = [r for r in rows if r.get("expected_answerable") is True]

    for row in rows:
        row["insufficient_evidence_detected"] = is_insufficient_evidence(row.get("answer", ""))

    correct_abstentions = sum(r["insufficient_evidence_detected"] for r in unanswerable)
    incorrect_abstentions = sum(r["insufficient_evidence_detected"] for r in answerable)

    result = {
        "challenge_version": payload.get("challenge_version", "unknown"),
        "n_total": len(rows),
        "n_unanswerable": len(unanswerable),
        "n_answerable": len(answerable),
        "insufficient_evidence_rate": correct_abstentions / len(unanswerable) if unanswerable else None,
        "false_abstention_rate": incorrect_abstentions / len(answerable) if answerable else None,
        "correct_abstentions": correct_abstentions,
        "incorrect_abstentions": incorrect_abstentions,
        "note": "This is an abstention-behavior metric, not retrieval recall. Human adjudication must precede scoring of the hard in-domain subset.",
        "responses": rows,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
