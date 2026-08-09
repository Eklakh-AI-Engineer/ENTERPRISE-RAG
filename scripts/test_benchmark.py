from app.evaluation.benchmark import (
    BenchmarkCase,
    RAGBenchmark,
)

from app.query.pipeline import QueryPipeline


def main():

    print("=" * 80)
    print("ENTERPRISE RAG BENCHMARK")
    print("=" * 80)

    pipeline = QueryPipeline(
        retrieval_top_k=10,
        rerank_top_k=5,
        candidate_k=10,
    )

    benchmark = RAGBenchmark(pipeline)

    cases = [

        # Case 1 — broad problem identification
        BenchmarkCase(
            query="What problems exist in the current job application process?",
            expected_chunks=[
                "sample-p001-c001",
                "sample-p001-c002",
                "sample-p001-c003",
            ],
        ),

        # Case 2 — efficiency / workflow reasoning
        BenchmarkCase(
            query="Why is the current job application process inefficient?",
            expected_chunks=[
                "sample-p001-c001",
                "sample-p001-c002",
                "sample-p001-c003",
            ],
        ),

        # Case 3 — specific evidence retrieval
        BenchmarkCase(
            query="What causes candidates to miss job opportunities?",
            expected_chunks=[
                "sample-p001-c002",
            ],
        ),
    ]

    results = benchmark.run(cases)

    print("\n")
    print("=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)

    for i, result in enumerate(
        results["cases"],
        start=1,
    ):

        print(f"\nCase {i}")
        print("-" * 80)

        print(
            "Query              :",
            result["query"],
        )

        print(
            "Expected chunks    :",
            result["expected_chunks"],
        )

        print(
            "Retrieved chunks   :",
            result["retrieved_chunks"],
        )

        print(
            "Matched chunks     :",
            result["matched_chunks"],
        )

        print(
            "Retrieval recall   :",
            result["retrieval_recall"],
        )

        print(
            "Citation chunks    :",
            result["citation_chunks"],
        )

        print(
            "Citation recall    :",
            result["citation_recall"],
        )

        print(
            "Overall score      :",
            result["overall_score"],
        )

        print(
            "Evaluation passed  :",
            result["evaluation_passed"],
        )

        print(
            "Passed             :",
            result["passed"],
        )

    print("\n")
    print("=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    print(
        "Total cases              :",
        results["total_cases"],
    )

    print(
        "Passed cases             :",
        results["passed_cases"],
    )

    print(
        "Average retrieval recall:",
        results["average_retrieval_recall"],
    )

    print(
        "Average citation recall :",
        results["average_citation_recall"],
    )

    print(
        "Average overall score   :",
        results["average_overall_score"],
    )

    print(
        "Pass rate               :",
        results["pass_rate"],
    )


if __name__ == "__main__":
    main()