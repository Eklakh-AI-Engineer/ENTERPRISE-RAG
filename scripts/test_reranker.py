import json

from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.hybrid.retriever import HybridRetriever
from app.reranking.cross_encoder import CrossEncoderReranker


def main():

    with open(
        "data/processed/sample_chunks.json",
        "r",
        encoding="utf-8",
    ) as file:
        chunks = json.load(file)

    # Build Dense
    dense = DenseRetriever()
    dense.build_index(chunks)

    # Build BM25
    bm25 = BM25Retriever()
    bm25.build_index(chunks)

    # Hybrid
    hybrid = HybridRetriever(
        dense_retriever=dense,
        bm25_retriever=bm25,
    )

    # Reranker
    print("\nLoading reranker...")
    reranker = CrossEncoderReranker()

    query = "How does the system optimize resumes?"

    print("\n" + "=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    # Get larger candidate pool
    candidates = hybrid.search(
        query,
        top_k=6,
        candidate_k=10,
    )

    print("\nHYBRID RESULTS:")
    print("-" * 80)

    for rank, result in enumerate(
        candidates,
        start=1,
    ):
        print(
            f"[{rank}] "
            f"RRF={result['rrf_score']:.6f} "
            f"page={result['page']} "
            f"chunk={result['chunk_id']}"
        )

    # Rerank
    results = reranker.rerank(
        query,
        candidates,
        top_k=3,
    )

    print("\nRERANKED RESULTS:")
    print("-" * 80)

    for rank, result in enumerate(
        results,
        start=1,
    ):

        print(
            f"\n[{rank}] "
            f"Rerank={result['rerank_score']:.4f} "
            f"page={result['page']} "
            f"chunk={result['chunk_id']}"
        )

        print(result["text"][:700])


if __name__ == "__main__":
    main()