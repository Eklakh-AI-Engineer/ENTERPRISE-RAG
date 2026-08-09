from app.faithfulness.checker import FaithfulnessChecker
from app.query.context import build_context

import json


def main():

    with open(
        "data/processed/sample_chunks.json",
        "r",
        encoding="utf-8"
    ) as f:
        chunks = json.load(f)

    context = build_context(chunks[:3])

    answer = """
The current job application process is highly manual. [Source 1]

A high-quality application typically requires 20–60 minutes
of manual effort. [Source 2]

Relevant jobs are scattered across multiple recruitment
platforms. [Source 2]
"""

    checker = FaithfulnessChecker()

    result = checker.check(
        answer=answer,
        context=context,
    )

    print("=" * 80)
    print("FAITHFULNESS RESULT")
    print("=" * 80)

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()