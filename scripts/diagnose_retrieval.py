from app.config.settings import settings

from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.hybrid.retriever import HybridRetriever
from app.reranking.cross_encoder import CrossEncoderReranker


def print_results(name, results):

    print("\n")
    print("=" * 80)
    print(name)
    print("=" * 80)

    for i, result in enumerate(results, start=1):

        print(f"\nRank {i}")
        print("-" * 80)

        print("Source   :", result.get("source"))
        print("Document :", result.get("document"))
        print("Page     :", result.get("page"))
        print("Chunk    :", result.get("chunk_id"))
        print("Score    :", result.get("score"))

        text = result.get("text", "")
        print("Text     :", text[:500].replace("\n", " "))


def main():

    query = "Why is the current job application process inefficient?"

    print("=" * 80)
    print("RETRIEVAL DIAGNOSTIC")
    print("=" * 80)

    print("\nQuery:")
    print(query)

    print("\nLoading dense retriever...")

    dense = DenseRetriever(
        model_name=settings.DENSE_MODEL
    )

    dense.load(
        settings.DENSE_INDEX_PATH,
        settings.DENSE_METADATA_PATH,
    )

    print("Loading BM25 retriever...")

    bm25 = BM25Retriever()

    bm25.load(
        settings.BM25_METADATA_PATH
    )

    print("Building hybrid retriever...")

    hybrid = HybridRetriever(
        dense_retriever=dense,
        bm25_retriever=bm25,
    )

    print("Loading reranker...")

    reranker = CrossEncoderReranker(
        model_name=settings.RERANKER_MODEL
    )

    dense_results = dense.search(
        query=query,
        top_k=10,
    )

    bm25_results = bm25.search(
        query=query,
        top_k=10,
    )

    hybrid_results = hybrid.search(
        query=query,
        top_k=10,
        candidate_k=10,
    )

    reranked_results = reranker.rerank(
        query=query,
        documents=hybrid_results,
        top_k=10,
    )

    print_results(
        "DENSE RETRIEVAL",
        dense_results,
    )

    print_results(
        "BM25 RETRIEVAL",
        bm25_results,
    )

    print_results(
        "HYBRID RETRIEVAL",
        hybrid_results,
    )

    print_results(
        "RERANKED RESULTS",
        reranked_results,
    )


if __name__ == "__main__":
    main()