from dataclasses import dataclass

from app.evaluation.retrieval_metrics import (
    recall_at_k,
    precision_at_k,
    hit_at_k,
    reciprocal_rank,
)


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

    def _extract_chunks(
        self,
        documents: list[dict],
    ) -> list[str]:

        return [
            document["chunk_id"]
            for document in documents
            if document.get("chunk_id")
        ]

    # ---------------------------------------------------------
    # Run single benchmark case
    # ---------------------------------------------------------

    def run_case(
        self,
        case: BenchmarkCase,
    ) -> dict:

        result = self.pipeline.run(case.query)

        expected_chunks = case.expected_chunks

        # -----------------------------------------------------
        # Retrieval metrics
        # -----------------------------------------------------

        retrieved_documents = result.get(
            "retrieved",
            [],
        )

        retrieved_chunks = self._extract_chunks(
            retrieved_documents
        )

        recall = recall_at_k(
            retrieved_chunks,
            expected_chunks,
        )

        precision = precision_at_k(
            retrieved_chunks,
            expected_chunks,
        )

        hit = hit_at_k(
            retrieved_chunks,
            expected_chunks,
        )

        mrr = reciprocal_rank(
            retrieved_chunks,
            expected_chunks,
        )

        matched_chunks = sorted(
            set(retrieved_chunks).intersection(
                set(expected_chunks)
            )
        )

        # -----------------------------------------------------
        # Citation metrics
        # -----------------------------------------------------

        citation_chunks = {
            citation.get("chunk_id")
            for citation in result.get("citations", [])
            if citation.get("chunk_id")
        }

        citation_matched = citation_chunks.intersection(
            set(expected_chunks)
        )

        # Citation Recall:
        # How many expected evidence chunks were actually cited?
        citation_recall = (
            len(citation_matched) / len(expected_chunks)
            if expected_chunks
            else 0.0
        )

        # Citation Precision:
        # How many cited chunks were actually relevant?
        citation_precision = (
            len(citation_matched) / len(citation_chunks)
            if citation_chunks
            else 0.0
        )

        # -----------------------------------------------------
        # Answer evaluation
        # -----------------------------------------------------

        evaluation = result.get(
            "evaluation",
            {},
        )

        overall_score = evaluation.get(
            "overall_score",
            0.0,
        )

        evaluation_passed = evaluation.get(
            "passed",
            False,
        )

        # -----------------------------------------------------
        # Final pass condition
        # -----------------------------------------------------

        passed = (
            recall >= 0.8
            and citation_recall >= 0.8
            and evaluation_passed
        )

        # -----------------------------------------------------
        # Case result
        # -----------------------------------------------------

        return {
            "query": case.query,

            "expected_chunks": sorted(
                expected_chunks
            ),

            "retrieved_chunks": retrieved_chunks,

            "matched_chunks": matched_chunks,

            # Retrieval
            "recall_at_k": round(
                recall,
                4,
            ),

            "precision_at_k": round(
                precision,
                4,
            ),

            "hit_at_k": round(
                hit,
                4,
            ),

            "reciprocal_rank": round(
                mrr,
                4,
            ),

            # Citations
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

            "citation_precision": round(
                citation_precision,
                4,
            ),

            # Answer evaluation
            "overall_score": round(
                overall_score,
                4,
            ),

            "evaluation_passed": evaluation_passed,

            # Final decision
            "passed": passed,
        }

    # ---------------------------------------------------------
    # Run complete benchmark
    # ---------------------------------------------------------

    def run(
        self,
        cases: list[BenchmarkCase],
    ) -> dict:

        case_results = []

        for case in cases:

            result = self.run_case(
                case
            )

            case_results.append(
                result
            )

        # -----------------------------------------------------
        # Aggregate metrics
        # -----------------------------------------------------

        if case_results:

            average_recall = sum(
                result["recall_at_k"]
                for result in case_results
            ) / len(case_results)

            average_precision = sum(
                result["precision_at_k"]
                for result in case_results
            ) / len(case_results)

            average_hit = sum(
                result["hit_at_k"]
                for result in case_results
            ) / len(case_results)

            average_mrr = sum(
                result["reciprocal_rank"]
                for result in case_results
            ) / len(case_results)

            average_citation_recall = sum(
                result["citation_recall"]
                for result in case_results
            ) / len(case_results)

            average_citation_precision = sum(
                result["citation_precision"]
                for result in case_results
            ) / len(case_results)

            average_overall_score = sum(
                result["overall_score"]
                for result in case_results
            ) / len(case_results)

            passed_cases = sum(
                result["passed"]
                for result in case_results
            )

            pass_rate = (
                passed_cases /
                len(case_results)
            )

        else:

            average_recall = 0.0
            average_precision = 0.0
            average_hit = 0.0
            average_mrr = 0.0
            average_citation_recall = 0.0
            average_citation_precision = 0.0
            average_overall_score = 0.0
            passed_cases = 0
            pass_rate = 0.0

        # -----------------------------------------------------
        # Final benchmark result
        # -----------------------------------------------------

        return {
            "cases": case_results,

            "average_recall": round(
                average_recall,
                4,
            ),

            "average_precision": round(
                average_precision,
                4,
            ),

            "average_hit": round(
                average_hit,
                4,
            ),

            "average_mrr": round(
                average_mrr,
                4,
            ),

            "average_citation_recall": round(
                average_citation_recall,
                4,
            ),

            "average_citation_precision": round(
                average_citation_precision,
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