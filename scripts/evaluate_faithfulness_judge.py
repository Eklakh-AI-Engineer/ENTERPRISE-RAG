#!/usr/bin/env python3
"""Validate a human subset for the faithfulness judge, including Cohen's kappa."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def cohens_kappa(human: list[bool], judge: list[bool]) -> float:
    if len(human) != len(judge) or not human:
        raise ValueError("Human and judge label vectors must have equal non-zero length.")

    n = len(human)
    observed = sum(a == b for a, b in zip(human, judge)) / n
    human_pos = sum(human) / n
    judge_pos = sum(judge) / n
    expected = (human_pos * judge_pos) + ((1 - human_pos) * (1 - judge_pos))
    return 1.0 if expected == 1.0 else (observed - expected) / (1 - expected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", default="data/evaluation/faithfulness_judge_validation.json")
    parser.add_argument("--min-items", type=int, default=30)
    args = parser.parse_args()

    payload = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if len(items) < args.min_items:
        raise ValueError(
            f"Faithfulness validation requires at least {args.min_items} independently reviewed claims; "
            f"received {len(items)}."
        )

    human = [bool(item["human_supported"]) for item in items]
    judge = [bool(item["judge_supported"]) for item in items]
    tp = sum(h and j for h, j in zip(human, judge))
    tn = sum((not h) and (not j) for h, j in zip(human, judge))
    fp = sum((not h) and j for h, j in zip(human, judge))
    fn = sum(h and (not j) for h, j in zip(human, judge))
    total = len(items)
    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    result = {
        "subset_version": payload["subset_version"],
        "judge_model": payload["judge_model"],
        "judge_prompt_version": payload["judge_prompt_version"],
        "judge_temperature": payload.get("judge_temperature"),
        "n": total,
        "confusion_matrix": {"true_positive": tp, "true_negative": tn, "false_positive": fp, "false_negative": fn},
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "cohens_kappa": cohens_kappa(human, judge),
        "interpretation": "Cohen's kappa measures agreement between the judge and independently reviewed human labels; human labels remain ground truth.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
