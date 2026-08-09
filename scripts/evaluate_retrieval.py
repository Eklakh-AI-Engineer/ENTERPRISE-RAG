import json

from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.hybrid.retriever import HybridRetriever
from app.reranking.cross_encoder import CrossEncoderReranker
from app.evaluation.retrieval_metrics import evaluate_results


CHUNKS_PATH = "data/processed/sample_chunks.json"
EVAL_PATH = "data/evaluation/retrieval_eval.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def evaluate_system(name, retrieve_function, evaluation_data):
    all_metrics = []

    print("\n" + "=" * 80)
    print(name)
    print("=" * 80)

    for item in evaluation_data:

        query = item["query"]
        relevant_chunks = item["relevant_chunks"]

        results = retrieve_function(query)

        metrics = evaluate_results(
            results,
            relevant_chunks,
            k_values=(1, 3, 5),
        )

        all_metrics.append(metrics)

        print(f"\nQuery: {query}")
        print(
            f"  Hit@1:    {metrics['hit@1']}"
        )
        print(
            f"  Hit@3:    {metrics['hit@3']}"
        )
        print(
            f"  Hit@5:    {metrics['hit@5']}"
        )
        print(
            f"  Recall@3: {metrics['recall@3']:.3f}"
        )
        print(
            f"  Recall@5: {metrics['recall@5']:.3f}"
        )
        print(
            f"  MRR:      {metrics['mrr']:.3f}"
        )

    count = len(all_metrics)

    average = {
        key: sum(
            metrics[key]
            for metrics in all_metrics
        ) / count
        for key in all_metrics[0]
    }

    print("\nAVERAGE")
    print("-" * 40)

    for key, value in average.items():
        print(f"{key:12}: {value:.3f}")

    return average


def main():

    chunks = load_json(CHUNKS_PATH)
    evaluation_data = load_json(EVAL_PATH)

    print(f"Chunks: {len(chunks)}")
    print(
        f"Evaluation queries: "
        f"{len(evaluation_data)}"
    )

    # --------------------------------------------------
    # Dense
    # --------------------------------------------------

    print("\nBuilding Dense retrieval...")

    dense = DenseRetriever()
    dense.build_index(chunks)

    dense_metrics = evaluate_system(
        "DENSE RETRIEVAL",
        lambda query: dense.search(
            query,
            top_k=5,
        ),
        evaluation_data,
    )

    # --------------------------------------------------
    # BM25
    # --------------------------------------------------

    print("\nBuilding BM25 retrieval...")

    bm25 = BM25Retriever()
    bm25.build_index(chunks)

    bm25_metrics = evaluate_system(
        "BM25 RETRIEVAL",
        lambda query: bm25.search(
            query,
            top_k=5,
        ),
        evaluation_data,
    )

    # --------------------------------------------------
    # Hybrid
    # --------------------------------------------------

    print("\nBuilding Hybrid retrieval...")

    hybrid = HybridRetriever(
        dense_retriever=dense,
        bm25_retriever=bm25,
    )

    hybrid_metrics = evaluate_system(
        "HYBRID RETRIEVAL",
        lambda query: hybrid.search(
            query,
            top_k=5,
            candidate_k=10,
        ),
        evaluation_data,
    )

    # --------------------------------------------------
    # Hybrid + Reranker
    # --------------------------------------------------

    print("\nLoading Cross-Encoder reranker...")

    reranker = CrossEncoderReranker()

    def reranked_search(query):

        candidates = hybrid.search(
            query,
            top_k=10,
            candidate_k=10,
        )

        return reranker.rerank(
            query,
            candidates,
            top_k=5,
        )

    reranked_metrics = evaluate_system(
        "HYBRID + RERANKER",
        reranked_search,
        evaluation_data,
    )

    # --------------------------------------------------
    # Final comparison
    # --------------------------------------------------

    print("\n\n" + "=" * 80)
    print("FINAL RETRIEVAL COMPARISON")
    print("=" * 80)

    systems = {
        "Dense": dense_metrics,
        "BM25": bm25_metrics,
        "Hybrid": hybrid_metrics,
        "Hybrid + Reranker": reranked_metrics,
    }

    print(
        f"\n{'System':<22}"
        f"{'Hit@3':>10}"
        f"{'Recall@5':>12}"
        f"{'MRR':>10}"
    )

    print("-" * 54)

    for name, metrics in systems.items():

        print(
            f"{name:<22}"
            f"{metrics['hit@3']:>10.3f}"
            f"{metrics['recall@5']:>12.3f}"
            f"{metrics['mrr']:>10.3f}"
        )


if __name__ == "__main__":
    main()