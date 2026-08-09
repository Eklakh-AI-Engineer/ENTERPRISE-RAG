import re


SOURCE_PATTERN = re.compile(
    r"\[Source\s+(\d+)\]",
    re.IGNORECASE,
)


def split_claims(answer: str) -> list[str]:
    """
    Extract answer statements that contain citations.
    """

    claims = []

    for line in answer.splitlines():

        line = line.strip()

        if not line:
            continue

        if SOURCE_PATTERN.search(line):
            claims.append(line)

    return claims


def extract_sources_from_claim(claim: str) -> list[int]:
    """
    Extract all [Source N] references from a claim.
    """

    return [
        int(match)
        for match in SOURCE_PATTERN.findall(claim)
    ]


def verify_claim_sources(
    answer: str,
    context_sources: list[dict],
) -> dict:
    """
    Verify that every cited claim references
    an existing retrieved source.

    This is a structural claim-level verifier.
    It does not yet use an LLM/NLI model to determine
    semantic entailment.
    """

    claims = split_claims(answer)

    verified_claims = []
    unsupported_claims = []

    for claim in claims:

        source_ids = extract_sources_from_claim(claim)

        valid_sources = []

        for source_id in source_ids:

            index = source_id - 1

            if 0 <= index < len(context_sources):
                valid_sources.append(source_id)

        if valid_sources:

            verified_claims.append(
                {
                    "claim": claim,
                    "sources": valid_sources,
                    "status": "SOURCE_EXISTS",
                }
            )

        else:

            unsupported_claims.append(
                {
                    "claim": claim,
                    "sources": source_ids,
                    "status": "INVALID_SOURCE",
                }
            )

    total_claims = len(claims)
    verified_count = len(verified_claims)

    if total_claims == 0:
        score = 0.0
    else:
        score = verified_count / total_claims

    return {
        "verified": len(unsupported_claims) == 0
        and total_claims > 0,
        "score": score,
        "total_claims": total_claims,
        "verified_claims": verified_claims,
        "unsupported_claims": unsupported_claims,
    }