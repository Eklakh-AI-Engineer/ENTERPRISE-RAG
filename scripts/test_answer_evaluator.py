from app.evaluation.answer_evaluator import AnswerEvaluator


def main():
    evaluator = AnswerEvaluator()

    query = "What problems exist in the current job application process?"

    answer = """
    The current job application process is highly manual.
    High-quality applications typically require 20–60 minutes.
    Relevant jobs are scattered across many recruitment platforms.
    [Source 1] [Source 99]
    """

    context_sources = [
        {
            "document": "sample.pdf",
            "page": 1,
            "chunk_id": "sample-p001-c001",
        },
        {
            "document": "sample.pdf",
            "page": 1,
            "chunk_id": "sample-p001-c002",
        },
        {
            "document": "sample.pdf",
            "page": 1,
            "chunk_id": "sample-p001-c003",
        },
    ]

    result = evaluator.evaluate(
        query=query,
        answer=answer,
        context_sources=context_sources,
    )

    print("=" * 80)
    print("ANSWER EVALUATION")
    print("=" * 80)

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()