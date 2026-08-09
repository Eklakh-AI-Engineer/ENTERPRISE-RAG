from app.evaluation.benchmark import BenchmarkCase, RAGBenchmark
from app.query.pipeline import QueryPipeline


def main():

    print("=" * 80)
    print("ENTERPRISE RAG BENCHMARK")
    print("=" * 80)

    pipeline = QueryPipeline(
    retrieval_top_k=10,
    rerank_top_k=8,
    candidate_k=10,
)

    benchmark = RAGBenchmark(pipeline)

    cases = [
        BenchmarkCase(
            query="What problems exist in the current job application process?",
            expected_sources=[1, 2, 3],
        ),
        BenchmarkCase(
            query="Why is the current job application process inefficient?",
            expected_sources=[2, 3],
        ),
        BenchmarkCase(
            query="What causes candidates to miss job opportunities?",
            expected_sources=[3],
        ),
    ]

    results = benchmark.run(cases)

    print("\n")
    print("=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)

    for i, result in enumerate(results["cases"], start=1):

        print(f"\nCase {i}")
        print("-" * 80)

        print("Query           :", result["query"])
        print("Expected sources:", result["expected_sources"])
        print("Actual sources  :", result["actual_sources"])
        print("Matched sources :", result["matched_sources"])
        print("Source recall   :", result["source_recall"])
        print("Overall score   :", result["overall_score"])
        print("Passed          :", result["passed"])

    print("\n")
    print("=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    print("Total cases          :", results["total_cases"])
    print("Passed cases         :", results["passed_cases"])
    print("Average source recall:", results["average_source_recall"])
    print("Average overall score:", results["average_overall_score"])
    print("Pass rate            :", results["pass_rate"])


if __name__ == "__main__":
    main()