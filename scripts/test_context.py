import json

from app.query.context import build_context


def main():

    with open(
        "data/processed/sample_chunks.json",
        "r",
        encoding="utf-8"
    ) as f:
        chunks = json.load(f)

    # Simulate retrieved results
    results = chunks[:3]

    context = build_context(results)

    print("=" * 80)
    print("ASSEMBLED CONTEXT")
    print("=" * 80)
    print(context)


if __name__ == "__main__":
    main()