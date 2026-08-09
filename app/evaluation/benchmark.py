from dataclasses import dataclass


@dataclass
class BenchmarkCase:
    query: str
    expected_sources: list[int]


class RAGBenchmark:

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def run_case(self, case: BenchmarkCase) -> dict:

        result = self.pipeline.run(case.query)

        actual_sources = {
            citation["source"]
            for citation in result["citations"]
        }

        expected_sources = set(case.expected_sources)

        matched_sources = actual_sources.intersection(
            expected_sources
        )

        source_recall = (
            len(matched_sources) / len(expected_sources)
            if expected_sources
            else 0.0
        )

        overall_score = result["evaluation"]["overall_score"]

        return {
            "query": case.query,
            "expected_sources": sorted(expected_sources),
            "actual_sources": sorted(actual_sources),
            "matched_sources": sorted(matched_sources),
            "source_recall": round(source_recall, 4),
            "overall_score": overall_score,
            "passed": (
                source_recall >= 0.8
                and result["evaluation"]["passed"]
            ),
        }

    def run(self, cases: list[BenchmarkCase]) -> dict:

        case_results = []

        for case in cases:
            result = self.run_case(case)
            case_results.append(result)

        if case_results:

            average_source_recall = sum(
                result["source_recall"]
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

            pass_rate = passed_cases / len(case_results)

        else:
            average_source_recall = 0.0
            average_overall_score = 0.0
            pass_rate = 0.0

        return {
            "cases": case_results,
            "average_source_recall": round(
                average_source_recall,
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
            "passed_cases": passed_cases if case_results else 0,
        }