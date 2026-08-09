import json

from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.hybrid.retriever import HybridRetriever


def main():

    with open(
        "data/processed/sample_chunks.json",
        "r",
        encoding="utf-8",
    ) as file:
        chunks = json.load(file)

    print(f"Loaded chunks: {len(chunks)}")

    # Dense
    dense = DenseRetriever()

    print("\nBuilding Dense index...")
    dense.build_index(chunks)

    # BM25
    bm25 = BM25Retriever()

    print("Building BM25 index...")
    bm25.build_index(chunks)

    # Hybrid
    hybrid = HybridRetriever(
        dense_retriever=dense,
        bm25_retriever=bm25,
    )

    queries = [
        "What problems exist in the current job application process?",
        "How does the proposed AI agent discover jobs?",
        "How does the system optimize resumes?",
    ]

    for query in queries:

        print("\n" + "=" * 80)
        print(f"QUERY: {query}")
        print("=" * 80)

        results = hybrid.search(
            query,
            top_k=3,
            candidate_k=10,
        )

        for rank, result in enumerate(
            results,
            start=1,
        ):

            print(
                f"\n[{rank}] "
                f"RRF={result['rrf_score']:.6f} "
                f"page={result['page']} "
                f"chunk={result['chunk_id']}"
            )

            print(result["text"][:500])


if __name__ == "__main__":
    main()