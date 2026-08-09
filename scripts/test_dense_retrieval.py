import json

from app.retrieval.dense.retriever import DenseRetriever


def main():

    with open(
        "data/processed/sample_chunks.json",
        "r",
        encoding="utf-8",
    ) as file:
        chunks = json.load(file)

    print(f"Loaded chunks: {len(chunks)}")

    retriever = DenseRetriever()

    print("Building FAISS index...")

    retriever.build_index(chunks)

    print("Index built successfully.")

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

        for rank, result in enumerate(results, start=1):

            print(
                f"\n[{rank}] "
                f"score={result['score']:.4f} "
                f"page={result['page']} "
                f"chunk={result['chunk_id']}"
            )

            print(result["text"][:500])

    retriever.save(
        "data/processed/dense.index",
        "data/processed/dense_metadata.json",
    )

    print("\nSaved:")
    print("data/processed/dense.index")
    print("data/processed/dense_metadata.json")


if __name__ == "__main__":
    main()