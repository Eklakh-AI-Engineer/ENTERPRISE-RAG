import re


# Matches citations like:
# [Source 1]
# [Source 2]
# [Source 10]
SOURCE_PATTERN = re.compile(
    r"\[Source\s+(\d+)\]",
    re.IGNORECASE,
)


def extract_source_ids(answer: str) -> list[int]:
    """
    Extract [Source N] references from the generated answer.

    Example:
        "Some fact [Source 1]. Another fact [Source 2]."

    Returns:
        [1, 2]
    """

    matches = SOURCE_PATTERN.findall(answer)

    source_ids = []

    # Preserve order while removing duplicates.
    for match in matches:
        source_id = int(match)

        if source_id not in source_ids:
            source_ids.append(source_id)

    return source_ids


def map_citations(
    answer: str,
    context_sources: list[dict],
) -> list[dict]:
    """
    Map [Source N] references from the LLM answer
    to the actual retrieved source metadata.

    Source numbering is based on the order in which
    reranked documents were inserted into the context.

    Example:

        [Source 1] -> context_sources[0]
        [Source 2] -> context_sources[1]
        [Source 3] -> context_sources[2]
    """

    source_ids = extract_source_ids(answer)

    citations = []

    for source_id in source_ids:

        # Source numbering is 1-based.
        index = source_id - 1

        # Ignore invalid source references.
        if index < 0 or index >= len(context_sources):
            continue

        source = context_sources[index]

        citations.append(
            {
                "source": source_id,
                "document": source.get(
                    "document",
                    "unknown",
                ),
                "document_id": source.get(
                    "document_id",
                ),
                "page": source.get(
                    "page",
                ),
                "section": source.get(
                    "section",
                ),
                "chunk_id": source.get(
                    "chunk_id",
                ),
            }
        )

    return citations