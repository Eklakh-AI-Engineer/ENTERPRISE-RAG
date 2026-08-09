from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.bm25.retriever import BM25Retriever


class HybridRetriever:

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        bm25_retriever: BM25Retriever,
        rrf_k: int = 60,
    ):
        self.dense = dense_retriever
        self.bm25 = bm25_retriever
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 5,
        candidate_k: int = 10,
    ) -> list[dict]:

        dense_results = self.dense.search(
            query,
            top_k=candidate_k,
        )

        bm25_results = self.bm25.search(
            query,
            top_k=candidate_k,
        )

        fused = {}

        for rank, result in enumerate(
            dense_results,
            start=1,
        ):
            chunk_id = result["chunk_id"]

            fused.setdefault(
                chunk_id,
                {
                    "chunk": result,
                    "rrf_score": 0.0,
                },
            )

            fused[chunk_id]["rrf_score"] += (
                1.0 / (self.rrf_k + rank)
            )

        for rank, result in enumerate(
            bm25_results,
            start=1,
        ):
            chunk_id = result["chunk_id"]

            fused.setdefault(
                chunk_id,
                {
                    "chunk": result,
                    "rrf_score": 0.0,
                },
            )

            fused[chunk_id]["rrf_score"] += (
                1.0 / (self.rrf_k + rank)
            )

        ranked = sorted(
            fused.values(),
            key=lambda item: item["rrf_score"],
            reverse=True,
        )

        results = []

        for item in ranked[:top_k]:
            result = item["chunk"].copy()
            result["rrf_score"] = item["rrf_score"]

            results.append(result)

        return results