from dataclasses import dataclass


@dataclass
class BenchmarkCase:
    query: str
    expected_chunks: list[str]


class RAGBenchmark:

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def _extract_chunks(self, documents: list[dict]) -> set[str]:
        return {
            document["chunk_id"]
            for document in documents
            if document.get("chunk_id")
        }

    def run_case(self, case: BenchmarkCase) -> dict:

        # Run complete RAG pipeline
        result = self.pipeline.run(case.query)

        expected_chunks = set(case.expected_chunks)

        # ---------------------------------------------------------
        # Retrieval evaluation
        # ---------------------------------------------------------

        retrieved_documents = result.get("retrieved", [])

        retrieved_chunks = self._extract_chunks(
            retrieved_documents
        )

        matched_chunks = (
            retrieved_chunks.intersection(expected_chunks)
        )

        retrieval_recall = (
            len(matched_chunks) / len(expected_chunks)
            if expected_chunks
            else 0.0
        )

        # ---------------------------------------------------------
        # Citation evaluation
        # ---------------------------------------------------------

        citation_chunks = {
            citation.get("chunk_id")
            for citation in result.get("citations", [])
            if citation.get("chunk_id")
        }

        citation_matched = (
            citation_chunks.intersection(expected_chunks)
        )

        citation_recall = (
            len(citation_matched) / len(expected_chunks)
            if expected_chunks
            else 0.0
        )

        # ---------------------------------------------------------
        # Answer evaluation
        # ---------------------------------------------------------

        evaluation = result["evaluation"]

        overall_score = evaluation["overall_score"]

        # ---------------------------------------------------------
        # Final pass condition
        # ---------------------------------------------------------

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

            "retrieved_chunks": sorted(
                retrieved_chunks
            ),

            "matched_chunks": sorted(
                matched_chunks
            ),

            "retrieval_recall": round(
                retrieval_recall,
                4,
            ),

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

            "overall_score": overall_score,

            "evaluation_passed": evaluation["passed"],

            "passed": passed,
        }

    def run(
        self,
        cases: list[BenchmarkCase],
    ) -> dict:

        case_results = []

        for case in cases:
            result = self.run_case(case)
            case_results.append(result)

        if case_results:

            average_retrieval_recall = sum(
                result["retrieval_recall"]
                for result in case_results
            ) / len(case_results)

            average_citation_recall = sum(
                result["citation_recall"]
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

            average_retrieval_recall = 0.0
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

            "total_cases": len(case_results),

            "passed_cases": passed_cases,
        }