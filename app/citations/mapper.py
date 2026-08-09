import re


SOURCE_PATTERN = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)


def extract_source_ids(answer: str) -> list[int]:
    """
    Extract [Source N] references from the generated answer.
    """

    matches = SOURCE_PATTERN.findall(answer)

    # Preserve order while removing duplicates
    source_ids = []

    for match in matches:
        source_id = int(match)

        if source_id not in source_ids:
            source_ids.append(source_id)

    return source_ids


def map_citations(answer: str, context_sources: list[dict]) -> list[dict]:
    """
    Map [Source N] references from the LLM answer
    to the actual retrieved source metadata.
    """

    source_ids = extract_source_ids(answer)

    citations = []

    for source_id in source_ids:

        # Source numbering is 1-based.
        index = source_id - 1

        if index < 0 or index >= len(context_sources):
            continue

        source = context_sources[index]

        citations.append(
            {
                "source": source_id,
                "document": source.get("document", "sample.pdf"),
                "page": source.get("page"),
                "chunk_id": source.get("chunk_id"),
            }
        )

    return citations