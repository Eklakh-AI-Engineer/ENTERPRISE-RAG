import json

from app.retrieval.bm25.retriever import BM25Retriever


def main():

    with open(
        "data/processed/sample_chunks.json",
        "r",
        encoding="utf-8",
    ) as file:
        chunks = json.load(file)

    print(f"Loaded chunks: {len(chunks)}")

    retriever = BM25Retriever()

    print("Building BM25 index...")

    retriever.build_index(chunks)

    print("BM25 index built successfully.")

    queries = [
        "What problems exist in the current job application process?",
        "How does the proposed AI agent discover jobs?",
        "How does the system optimize resumes?",
    ]

    for query in queries:

        print("\n" + "=" * 80)
        print(f"QUERY: {query}")
        print("=" * 80)

        results = retriever.search(
            query,
            top_k=3,
        )

        for rank, result in enumerate(
            results,
            start=1,
        ):

            print(
                f"\n[{rank}] "
                f"score={result['score']:.4f} "
                f"page={result['page']} "
                f"chunk={result['chunk_id']}"
            )

            print(result["text"][:500])

    retriever.save(
        "data/processed/bm25_metadata.json"
    )

    print("\nSaved:")
    print("data/processed/bm25_metadata.json")


if __name__ == "__main__":
    main()