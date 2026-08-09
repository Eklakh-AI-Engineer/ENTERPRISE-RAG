from app.citations.mapper import (
    extract_source_ids,
    map_citations,
)


def main():

    answer = """
    The application process is highly manual. [Source 1]

    Applications can require 20–60 minutes of effort. [Source 2]

    Job discovery is fragmented across multiple platforms. [Source 2] [Source 3]
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

    print("=" * 80)
    print("EXTRACTED SOURCE IDS")
    print("=" * 80)

    source_ids = extract_source_ids(answer)

    print(source_ids)

    print("\n" + "=" * 80)
    print("MAPPED CITATIONS")
    print("=" * 80)

    citations = map_citations(
        answer,
        context_sources,
    )

    for citation in citations:
        print(citation)


if __name__ == "__main__":
    main()