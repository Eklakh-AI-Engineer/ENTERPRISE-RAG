from app.query.pipeline import QueryPipeline


def main():

    print("=" * 80)
    print("INITIALIZING ENTERPRISE RAG QUERY PIPELINE")
    print("=" * 80)

    pipeline = QueryPipeline(
        retrieval_top_k=10,
        rerank_top_k=5,
        candidate_k=10,
    )

    query = "What problems exist in the current job application process?"

    print("\n")
    print("=" * 80)
    print("QUERY")
    print("=" * 80)
    print(query)

    result = pipeline.run(query)

    print("\n")
    print("=" * 80)
    print("FINAL RAG ANSWER")
    print("=" * 80)
    print(result["answer"])

    print("\n")
    print("=" * 80)
    print("CITATIONS")
    print("=" * 80)

    for citation in result["citations"]:
        print(citation)

    print("\n")
    print("=" * 80)
    print("PIPELINE STATISTICS")
    print("=" * 80)

    print("Retrieved documents :", result["retrieved_count"])
    print("Reranked documents  :", result["reranked_count"])

    print("\n")
    print("=" * 80)
    print("ANSWER EVALUATION")
    print("=" * 80)

    evaluation = result["evaluation"]

    print("Citation score      :", evaluation["citation_score"])
    print("Relevance score     :", evaluation["relevance_score"])
    print("Support score       :", evaluation["support_score"])
    print("Overall score       :", evaluation["overall_score"])
    print("Total citations     :", evaluation["total_citations"])
    print("Valid citations     :", evaluation["valid_citations"])
    print("Invalid citations   :", evaluation["invalid_citations"])
    print("Evaluation passed   :", evaluation["passed"])


if __name__ == "__main__":
    main()