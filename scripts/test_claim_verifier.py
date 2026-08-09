from app.citations.claim_verifier import verify_claim_sources


def main():

    answer = """
    The job application process is highly manual. [Source 1]
    High-quality applications typically require 20–60 minutes. [Source 2]
    This system uses quantum computing. [Source 99]
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

    result = verify_claim_sources(
        answer,
        context_sources,
    )

    print("=" * 80)
    print("CLAIM-LEVEL CITATION VERIFICATION")
    print("=" * 80)

    print(result)


if __name__ == "__main__":
    main()