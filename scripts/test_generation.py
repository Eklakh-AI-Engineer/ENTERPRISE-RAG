from app.generation.rag_generator import RAGGenerator
from app.query.context import build_context

import json


def main():

    with open(
        "data/processed/sample_chunks.json",
        "r",
        encoding="utf-8"
    ) as f:
        chunks = json.load(f)

    results = chunks[:3]

    context = build_context(results)

    query = "What problems exist in the current job application process?"

    generator = RAGGenerator()

    response = generator.generate(
        query=query,
        context=context,
    )

    print("=" * 80)
    print("RAG ANSWER")
    print("=" * 80)
    print(response)


if __name__ == "__main__":
    main()