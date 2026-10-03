import re
from typing import Any


SOURCE_PATTERN = re.compile(
    r"\[Source\s+(\d+)\]",
    re.IGNORECASE,
)


class CitationVerifier:
    """
    Deterministic citation verifier.

    Verifies:

    1. Citation syntax
    2. Citation existence
    3. Citation-to-source mapping
    4. Whether cited claims have lexical evidence
       in the cited retrieved source

    This verifier does not call an LLM.
    """

    def verify(
        self,
        answer: str,
        context_sources: list[dict],
    ) -> dict:

        source_ids = self._extract_source_ids(answer)

        valid_source_ids = {
            index
            for index in range(
                1,
                len(context_sources) + 1,
            )
        }

        valid_citations = [
            source_id
            for source_id in source_ids
            if source_id in valid_source_ids
        ]

        invalid_citations = [
            source_id
            for source_id in source_ids
            if source_id not in valid_source_ids
        ]

        citation_claims = self._extract_citation_claims(
            answer
        )

        claim_results = []

        for claim in citation_claims:

            source_id = claim["source"]

            if source_id not in valid_source_ids:

                claim_results.append(
                    {
                        "claim": claim["claim"],
                        "source": source_id,
                        "valid_source": False,
                        "supported": False,
                        "evidence_score": 0.0,
                    }
                )

                continue

            source = context_sources[source_id - 1]

            evidence_text = self._get_source_text(
                source
            )

            evidence_score = self._calculate_evidence_score(
                claim["claim"],
                evidence_text,
            )

            claim_results.append(
                {
                    "claim": claim["claim"],
                    "source": source_id,
                    "valid_source": True,
                    "supported": evidence_score >= 0.20,
                    "evidence_score": round(
                        evidence_score,
                        4,
                    ),
                }
            )

        supported_claims = sum(
            1
            for result in claim_results
            if result["supported"]
        )

        total_claims = len(claim_results)

        support_score = (
            supported_claims / total_claims
            if total_claims
            else 0.0
        )

        citation_accuracy = (
            len(valid_citations) / len(source_ids)
            if source_ids
            else 0.0
        )

        return {
            "valid": (
                len(invalid_citations) == 0
                and support_score >= 0.75
            ),
            "total_citations": len(source_ids),
            "valid_citations": valid_citations,
            "invalid_citations": invalid_citations,
            "citation_accuracy": round(
                citation_accuracy,
                4,
            ),
            "claim_count": total_claims,
            "supported_claims": supported_claims,
            "unsupported_claims": (
                total_claims - supported_claims
            ),
            "support_score": round(
                support_score,
                4,
            ),
            "claims": claim_results,
        }

    # ---------------------------------------------------------
    # Citation extraction
    # ---------------------------------------------------------

    def _extract_source_ids(
        self,
        answer: str,
    ) -> list[int]:

        matches = SOURCE_PATTERN.findall(answer)

        source_ids = []

        for match in matches:

            source_id = int(match)

            if source_id not in source_ids:
                source_ids.append(source_id)

        return source_ids

    # ---------------------------------------------------------
    # Claim / citation extraction
    # ---------------------------------------------------------

    def _extract_citation_claims(
        self,
        answer: str,
    ) -> list[dict]:
        claims = []

        for match in SOURCE_PATTERN.finditer(answer):
            prefix = answer[:match.start()].rstrip()
            if not prefix:
                continue

            # Citations commonly appear after sentence-ending punctuation,
            # e.g. "Claim text. [Source 1]". Use the final sentence before
            # the marker so punctuation does not discard the cited claim.
            sentences = re.split(
                r"(?<=[.!?])\s+",
                prefix,
            )
            claim_text = sentences[-1].strip()
            if not claim_text:
                continue

            claims.append(
                {
                    "claim": claim_text,
                    "source": int(match.group(1)),
                }
            )

        return claims

    # ---------------------------------------------------------
    # Source text extraction
    # ---------------------------------------------------------

    @staticmethod
    def _get_source_text(
        source: dict[str, Any],
    ) -> str:

        possible_fields = [
            "text",
            "content",
            "chunk",
            "document_text",
            "page_content",
        ]

        for field in possible_fields:

            value = source.get(field)

            if isinstance(value, str):
                return value

        return ""

    # ---------------------------------------------------------
    # Evidence scoring
    # ---------------------------------------------------------

    def _calculate_evidence_score(
        self,
        claim: str,
        evidence: str,
    ) -> float:

        if not claim.strip() or not evidence.strip():
            return 0.0

        claim_tokens = self._tokenize(claim)

        evidence_tokens = self._tokenize(
            evidence
        )

        if not claim_tokens or not evidence_tokens:
            return 0.0

        evidence_set = set(evidence_tokens)

        overlap = sum(
            1
            for token in claim_tokens
            if token in evidence_set
        )

        return overlap / len(claim_tokens)

    # ---------------------------------------------------------
    # Tokenization
    # ---------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> list[str]:

        return re.findall(
            r"\b[a-zA-Z0-9]+\b",
            text.lower(),
        )