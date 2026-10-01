#!/usr/bin/env python3
"""Compare the LLM faithfulness judge with human labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", default="data/evaluation/faithfulness_judge_validation.json")
    args = parser.parse_args()

    payload = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    items = payload["items"]

    tp = sum(i["judge_supported"] and i["human_supported"] for i in items)
    tn = sum(not i["judge_supported"] and not i["human_supported"] for i in items)
    fp = sum(i["judge_supported"] and not i["human_supported"] for i in items)
    fn = sum(not i["judge_supported"] and i["human_supported"] for i in items)

    total = len(items)
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    result = {
        "subset_version": payload["subset_version"],
        "judge_model": payload["judge_model"],
        "judge_prompt_version": payload["judge_prompt_version"],
        "judge_temperature": payload.get("judge_temperature"),
        "n": total,
        "confusion_matrix": {
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
        },
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
