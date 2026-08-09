from dataclasses import dataclass
from math import log2


@dataclass
class BenchmarkCase:
    query: str
    expected_chunks: list[str]


class RAGBenchmark:

    def __init__(self, pipeline):
        self.pipeline = pipeline

    # ---------------------------------------------------------
    # Utility
    # ---------------------------------------------------------

    def _extract_chunks(self, documents: list[dict]) -> list[str]:
        """
        Preserve retrieval ranking order while extracting chunk IDs.
        """
        chunks = []

        for document in documents:
            chunk_id = document.get("chunk_id")

            if chunk_id and chunk_id not in chunks:
                chunks.append(chunk_id)

        return chunks

    # ---------------------------------------------------------
    # Retrieval Metrics
    # ---------------------------------------------------------

    def _recall_at_k(
        self,
        retrieved_chunks: list[str],
        expected_chunks: set[str],
        k: int,
    ) -> float:

        if not expected_chunks:
            return 0.0

        retrieved_at_k = retrieved_chunks[:k]

        matched = (
            set(retrieved_at_k)
            .intersection(expected_chunks)
        )

        return len(matched) / len(expected_chunks)

    def _precision_at_k(
        self,
        retrieved_chunks: list[str],
        expected_chunks: set[str],
        k: int,
    ) -> float:

        retrieved_at_k = retrieved_chunks[:k]

        if not retrieved_at_k:
            return 0.0

        relevant = (
            set(retrieved_at_k)
            .intersection(expected_chunks)
        )

        return len(relevant) / len(retrieved_at_k)

    def _mrr(
        self,
        retrieved_chunks: list[str],
        expected_chunks: set[str],
    ) -> float:

        for rank, chunk_id in enumerate(
            retrieved_chunks,
            start=1,
        ):
            if chunk_id in expected_chunks:
                return 1.0 / rank

        return 0.0

    def _ndcg_at_k(
        self,
        retrieved_chunks: list[str],
        expected_chunks: set[str],
        k: int,
    ) -> float:

        retrieved_at_k = retrieved_chunks[:k]

        if not expected_chunks:
            return 0.0

        # Binary relevance:
        # 1 = expected chunk
        # 0 = irrelevant chunk
        dcg = 0.0

        for rank, chunk_id in enumerate(
            retrieved_at_k,
            start=1,
        ):
            relevance = (
                1
                if chunk_id in expected_chunks
                else 0
            )

            dcg += relevance / log2(rank + 1)

        # Ideal ranking
        ideal_relevant = min(
            len(expected_chunks),
            k,
        )

        idcg = sum(
            1 / log2(rank + 1)
            for rank in range(
                1,
                ideal_relevant + 1,
            )
        )

        if idcg == 0:
            return 0.0

        return dcg / idcg

    # ---------------------------------------------------------
    # Single Case
    # ---------------------------------------------------------

    def run_case(
        self,
        case: BenchmarkCase,
    ) -> dict:

        result = self.pipeline.run(case.query)

        expected_chunks = set(
            case.expected_chunks
        )

        # -----------------------------------------------------
        # Retrieved documents
        # -----------------------------------------------------

        retrieved_documents = result.get(
            "retrieved",
            [],
        )

        retrieved_chunks = self._extract_chunks(
            retrieved_documents
        )

        matched_chunks = (
            set(retrieved_chunks)
            .intersection(expected_chunks)
        )

        # -----------------------------------------------------
        # Retrieval metrics
        # -----------------------------------------------------

        recall_at_5 = self._recall_at_k(
            retrieved_chunks,
            expected_chunks,
            5,
        )

        precision_at_5 = self._precision_at_k(
            retrieved_chunks,
            expected_chunks,
            5,
        )

        mrr = self._mrr(
            retrieved_chunks,
            expected_chunks,
        )

        ndcg_at_5 = self._ndcg_at_k(
            retrieved_chunks,
            expected_chunks,
            5,
        )

        # Preserve previous metric
        retrieval_recall = (
            len(matched_chunks)
            / len(expected_chunks)
            if expected_chunks
            else 0.0
        )

        # -----------------------------------------------------
        # Citation evaluation
        # -----------------------------------------------------

        citation_chunks = {
            citation.get("chunk_id")
            for citation in result.get(
                "citations",
                [],
            )
            if citation.get("chunk_id")
        }

        citation_matched = (
            citation_chunks.intersection(
                expected_chunks
            )
        )

        citation_recall = (
            len(citation_matched)
            / len(expected_chunks)
            if expected_chunks
            else 0.0
        )

        # -----------------------------------------------------
        # Answer evaluation
        # -----------------------------------------------------

        evaluation = result["evaluation"]

        overall_score = evaluation[
            "overall_score"
        ]

        # -----------------------------------------------------
        # Final pass condition
        # -----------------------------------------------------

        passed = (
            retrieval_recall >= 0.8
            and citation_recall >= 0.8
            and evaluation["passed"]
        )

        return {
            "query": case.query,

            "expected_chunks": sorted(
                expected_chunks
            ),

            "retrieved_chunks": retrieved_chunks,

            "matched_chunks": sorted(
                matched_chunks
            ),

            # Existing retrieval metric
            "retrieval_recall": round(
                retrieval_recall,
                4,
            ),

            # New IR metrics
            "recall_at_5": round(
                recall_at_5,
                4,
            ),

            "precision_at_5": round(
                precision_at_5,
                4,
            ),

            "mrr": round(
                mrr,
                4,
            ),

            "ndcg_at_5": round(
                ndcg_at_5,
                4,
            ),

            # Citation metrics
            "citation_chunks": sorted(
                citation_chunks
            ),

            "citation_matched_chunks": sorted(
                citation_matched
            ),

            "citation_recall": round(
                citation_recall,
                4,
            ),

            # Answer evaluation
            "overall_score": overall_score,

            "evaluation_passed": evaluation[
                "passed"
            ],

            "passed": passed,
        }

    # ---------------------------------------------------------
    # Full Benchmark
    # ---------------------------------------------------------

    def run(
        self,
        cases: list[BenchmarkCase],
    ) -> dict:

        case_results = []

        for case in cases:
            result = self.run_case(case)
            case_results.append(result)

        if case_results:

            average_retrieval_recall = (
                sum(
                    result[
                        "retrieval_recall"
                    ]
                    for result in case_results
                )
                / len(case_results)
            )

            average_recall_at_5 = (
                sum(
                    result[
                        "recall_at_5"
                    ]
                    for result in case_results
                )
                / len(case_results)
            )

            average_precision_at_5 = (
                sum(
                    result[
                        "precision_at_5"
                    ]
                    for result in case_results
                )
                / len(case_results)
            )

            average_mrr = (
                sum(
                    result["mrr"]
                    for result in case_results
                )
                / len(case_results)
            )

            average_ndcg_at_5 = (
                sum(
                    result[
                        "ndcg_at_5"
                    ]
                    for result in case_results
                )
                / len(case_results)
            )

            average_citation_recall = (
                sum(
                    result[
                        "citation_recall"
                    ]
                    for result in case_results
                )
                / len(case_results)
            )

            average_overall_score = (
                sum(
                    result[
                        "overall_score"
                    ]
                    for result in case_results
                )
                / len(case_results)
            )

            passed_cases = sum(
                result["passed"]
                for result in case_results
            )

            pass_rate = (
                passed_cases
                / len(case_results)
            )

        else:

            average_retrieval_recall = 0.0
            average_recall_at_5 = 0.0
            average_precision_at_5 = 0.0
            average_mrr = 0.0
            average_ndcg_at_5 = 0.0
            average_citation_recall = 0.0
            average_overall_score = 0.0
            passed_cases = 0
            pass_rate = 0.0

        return {
            "cases": case_results,

            "average_retrieval_recall": round(
                average_retrieval_recall,
                4,
            ),

            "average_recall_at_5": round(
                average_recall_at_5,
                4,
            ),

            "average_precision_at_5": round(
                average_precision_at_5,
                4,
            ),

            "average_mrr": round(
                average_mrr,
                4,
            ),

            "average_ndcg_at_5": round(
                average_ndcg_at_5,
                4,
            ),

            "average_citation_recall": round(
                average_citation_recall,
                4,
            ),

            "average_overall_score": round(
                average_overall_score,
                4,
            ),

            "pass_rate": round(
                pass_rate,
                4,
            ),

            "total_cases": len(
                case_results
            ),

            "passed_cases": passed_cases,
        }