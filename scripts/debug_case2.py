from app.query.pipeline import QueryPipeline


def main():

    query = "Why is the current job application process inefficient?"

    pipeline = QueryPipeline(
        retrieval_top_k=10,
        rerank_top_k=10,
        candidate_k=10,
    )

    print("\n" + "=" * 80)
    print("CASE 2 RETRIEVAL DEBUG")
    print("=" * 80)

    # ---------------------------------------------------------
    # Dense
    # ---------------------------------------------------------

    dense = pipeline.dense.search(
        query,
        top_k=10,
    )

    print("\nDENSE RESULTS")
    print("-" * 80)

    for rank, item in enumerate(dense, start=1):
        print(
            rank,
            item["chunk_id"],
            "source=",
            item.get("source"),
            "score=",
            round(item.get("score", 0), 4),
        )

    # ---------------------------------------------------------
    # BM25
    # ---------------------------------------------------------

    bm25 = pipeline.bm25.search(
        query,
        top_k=10,
    )

    print("\nBM25 RESULTS")
    print("-" * 80)

    for rank, item in enumerate(bm25, start=1):
        print(
            rank,
            item["chunk_id"],
            "source=",
            item.get("source"),
            "score=",
            round(item.get("score", 0), 4),
        )

    # ---------------------------------------------------------
    # Hybrid
    # ---------------------------------------------------------

    hybrid = pipeline.hybrid.search(
        query,
        top_k=10,
        candidate_k=10,
    )

    print("\nHYBRID RESULTS")
    print("-" * 80)

    for rank, item in enumerate(hybrid, start=1):
        print(
            rank,
            item["chunk_id"],
            "source=",
            item.get("source"),
            "rrf=",
            round(item.get("rrf_score", 0), 6),
        )

    # ---------------------------------------------------------
    # Reranker
    # ---------------------------------------------------------

    reranked = pipeline.reranker.rerank(
        query,
        hybrid,
        top_k=10,
    )

    print("\nRERANKED RESULTS")
    print("-" * 80)

    for rank, item in enumerate(reranked, start=1):
        print(
            rank,
            item["chunk_id"],
            "source=",
            item.get("source"),
            "rerank=",
            round(item.get("rerank_score", 0), 4),
        )


if __name__ == "__main__":
    main()