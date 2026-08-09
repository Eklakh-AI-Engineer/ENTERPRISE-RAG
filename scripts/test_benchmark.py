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

        # ---------------------------------------------------------
        # Problem understanding
        # ---------------------------------------------------------

        BenchmarkCase(
            query="What problems exist in the current job application process?",
            expected_chunks=[
                "sample-p001-c001",
                "sample-p001-c002",
                "sample-p001-c003",
            ],
        ),

        BenchmarkCase(
            query="Why is the current job application process inefficient?",
            expected_chunks=[
                "sample-p001-c001",
                "sample-p001-c002",
                "sample-p001-c003",
            ],
        ),

        BenchmarkCase(
            query="What causes candidates to miss job opportunities?",
            expected_chunks=[
                "sample-p001-c002",
            ],
        ),

        # ---------------------------------------------------------
        # Application workflow
        # ---------------------------------------------------------

        BenchmarkCase(
            query="Why do candidates spend so much time applying for jobs?",
            expected_chunks=[
                "sample-p001-c001",
                "sample-p001-c002",
            ],
        ),

        BenchmarkCase(
            query="What repetitive tasks do job applicants perform?",
            expected_chunks=[
                "sample-p001-c002",
                "sample-p001-c003",
            ],
        ),

        BenchmarkCase(
            query="Why is job discovery difficult for candidates?",
            expected_chunks=[
                "sample-p001-c001",
                "sample-p001-c003",
            ],
        ),

        # ---------------------------------------------------------
        # ATS / personalization
        # ---------------------------------------------------------

        BenchmarkCase(
            query="Why do candidates need to customize their resumes?",
            expected_chunks=[
                "sample-p001-c001",
                "sample-p001-c002",
            ],
        ),

        BenchmarkCase(
            query="What is the problem with using a generic resume?",
            expected_chunks=[
                "sample-p001-c002",
            ],
        ),

        BenchmarkCase(
            query="Why is personalization difficult at scale?",
            expected_chunks=[
                "sample-p001-c002",
            ],
        ),

        # ---------------------------------------------------------
        # Administrative problems
        # ---------------------------------------------------------

        BenchmarkCase(
            query="Why do applicants repeatedly enter the same information?",
            expected_chunks=[
                "sample-p001-c003",
            ],
        ),

        BenchmarkCase(
            query="How do manual processes affect application quality?",
            expected_chunks=[
                "sample-p001-c003",
            ],
        ),

        BenchmarkCase(
            query="What makes the current hiring workflow difficult to scale?",
            expected_chunks=[
                "sample-p001-c003",
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
            "Recall@K           :",
            result["recall_at_k"],
        )

        print(
            "Precision@K        :",
            result["precision_at_k"],
        )

        print(
            "Hit@K              :",
            result["hit_at_k"],
        )

        print(
            "Reciprocal Rank    :",
            result["reciprocal_rank"],
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
        "Average Recall@K         :",
        results["average_recall"],
    )

    print(
        "Average Precision@K      :",
        results["average_precision"],
    )

    print(
        "Average Hit@K            :",
        results["average_hit"],
    )

    print(
        "Average MRR              :",
        results["average_mrr"],
    )

    print(
        "Average Citation Recall  :",
        results["average_citation_recall"],
    )

    print(
        "Average Overall Score    :",
        results["average_overall_score"],
    )

    print(
        "Pass Rate                :",
        results["pass_rate"],
    )


if __name__ == "__main__":
    main()