import re


SOURCE_PATTERN = re.compile(
    r"\[Source\s+(\d+)\]",
    re.IGNORECASE,
)


def extract_source_ids(answer: str) -> list[int]:
    """
    Extract [Source N] references from the generated answer.
    """

    matches = SOURCE_PATTERN.findall(answer)

    source_ids = []

    for match in matches:
        source_id = int(match)

        if source_id not in source_ids:
            source_ids.append(source_id)

    return source_ids


def verify_citations(
    answer: str,
    context_sources: list[dict],
) -> dict:
    """
    Verify that every [Source N] citation in the answer
    points to an existing retrieved source.
    """

    source_ids = extract_source_ids(answer)

    valid_sources = []
    invalid_sources = []

    for source_id in source_ids:

        # Source numbering is 1-based.
        index = source_id - 1

        if 0 <= index < len(context_sources):
            valid_sources.append(source_id)
        else:
            invalid_sources.append(source_id)

    total = len(source_ids)
    valid_count = len(valid_sources)

    if total == 0:
        score = 0.0
    else:
        score = valid_count / total

    return {
        "verified": len(invalid_sources) == 0 and total > 0,
        "score": score,
        "total_citations": total,
        "valid_citations": valid_sources,
        "invalid_citations": invalid_sources,
    }