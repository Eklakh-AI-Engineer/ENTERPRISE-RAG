import json
import os
import re

from app.generation.openrouter import OpenRouterClient


class FaithfulnessVerifier:
    JUDGE_PROMPT_VERSION = "faithfulness-v1"
    JUDGE_TEMPERATURE = 0.0
    """
    Verifies whether claims in a generated answer are
    supported by the retrieved evidence.

    This is semantic evidence verification, not merely
    citation-ID validation.
    """

    SOURCE_PATTERN = re.compile(
        r"\[Source\s+(\d+)\]",
        re.IGNORECASE,
    )

    def __init__(self):
        self.llm = OpenRouterClient()

    # =====================================================
    # PUBLIC API
    # =====================================================

    def verify(
        self,
        answer: str,
        context_sources: list[dict],
    ) -> dict:
        """
        Verify claims in the answer against the
        cited source content.
        """

        claims = self._extract_claims(answer)

        if not claims:
            return {
                "faithfulness_score": 0.0,
                "judge_model": getattr(self.llm, "model", os.getenv("OPENROUTER_MODEL", "")),
                "judge_prompt_version": self.JUDGE_PROMPT_VERSION,
                "judge_temperature": self.JUDGE_TEMPERATURE,
                "total_claims": 0,
                "supported_claims": 0,
                "unsupported_claims": 0,
                "claims": [],
            }

        verified_claims = []

        for claim in claims:

            source_ids = claim["source_ids"]

            evidence = []

            for source_id in source_ids:

                # Source numbering is 1-based.
                index = source_id - 1

                if (
                    index < 0
                    or index >= len(context_sources)
                ):
                    continue

                source = context_sources[index]

                evidence.append(
                    {
                        "source": source_id,
                        "document": source.get("document"),
                        "page": source.get("page"),
                        "chunk_id": source.get("chunk_id"),
                        "text": source.get("text", ""),
                    }
                )

            verification = self._verify_claim(
                claim=claim["claim"],
                evidence=evidence,
            )

            verified_claims.append(
                {
                    "claim": claim["claim"],
                    "source_ids": source_ids,
                    "supported": verification["supported"],
                    "confidence": verification["confidence"],
                    "reason": verification["reason"],
                }
            )

        supported = sum(
            1
            for item in verified_claims
            if item["supported"]
        )

        total = len(verified_claims)

        faithfulness_score = (
            supported / total
            if total
            else 0.0
        )

        return {
            "faithfulness_score": round(
                faithfulness_score,
                4,
            ),
            "judge_model": getattr(self.llm, "model", os.getenv("OPENROUTER_MODEL", "")),
            "judge_prompt_version": self.JUDGE_PROMPT_VERSION,
            "judge_temperature": self.JUDGE_TEMPERATURE,
            "total_claims": total,
            "supported_claims": supported,
            "unsupported_claims": total - supported,
            "claims": verified_claims,
        }

    # =====================================================
    # CLAIM EXTRACTION
    # =====================================================

    def _extract_claims(
        self,
        answer: str,
    ) -> list[dict]:
        """
        Extract claims and associate [Source N] citations
        with the sentence immediately preceding them.

        Handles:

            Claim. [Source 1]

            Claim. [Source 1] [Source 2]

            Claim [Source 1].
        """

        claims = []

        answer = re.sub(
            r"\s+",
            " ",
            answer.strip(),
        )

        if not answer:
            return []

        # -------------------------------------------------
        # Split while keeping citation markers attached.
        # -------------------------------------------------

        pattern = re.compile(
            r"""
            (
                .*?
                (?:
                    \[Source\s+\d+\]
                    (?:\s*\[Source\s+\d+\])*
                )
            )
            (?:
                (?=\s+|$)
            )
            """,
            re.IGNORECASE | re.VERBOSE,
        )

        matches = pattern.findall(answer)

        if not matches:
            return [
                {
                    "claim": answer,
                    "source_ids": [],
                }
            ]

        for block in matches:

            block = block.strip()

            if not block:
                continue

            source_matches = self.SOURCE_PATTERN.findall(
                block
            )

            source_ids = []

            for match in source_matches:

                source_id = int(match)

                if source_id not in source_ids:
                    source_ids.append(source_id)

            claim = self.SOURCE_PATTERN.sub(
                "",
                block,
            )

            claim = re.sub(
                r"\s+",
                " ",
                claim,
            ).strip()

            if not claim:
                continue

            # Remove trailing punctuation artifacts.
            claim = claim.rstrip()

            claims.append(
                {
                    "claim": claim,
                    "source_ids": source_ids,
                }
            )

        return claims

    # =====================================================
    # LLM EVIDENCE VERIFICATION
    # =====================================================

    def _verify_claim(
        self,
        claim: str,
        evidence: list[dict],
    ) -> dict:
        """
        Ask the LLM whether the supplied evidence
        entails the claim.

        The verifier is explicitly forbidden from
        using outside knowledge.
        """

        if not evidence:
            return {
                "supported": False,
                "confidence": 0.0,
                "reason": "No valid cited evidence was found.",
            }

        evidence_blocks = []

        for item in evidence:

            evidence_blocks.append(
                f"""
[SOURCE {item["source"]}]
Document: {item["document"]}
Page: {item["page"]}
Chunk: {item["chunk_id"]}

{item["text"]}
"""
            )

        evidence_text = "\n".join(
            evidence_blocks
        )

        prompt = f"""
You are an evidence verification system.

Your ONLY task is to determine whether the supplied
evidence supports the supplied claim.

Do NOT use outside knowledge.

CLAIM:
{claim}

EVIDENCE:
{evidence_text}

Rules:

1. Mark supported=true only when the evidence directly
   supports the claim.
2. If the evidence contradicts the claim, return false.
3. If the evidence is insufficient, return false.
4. Do not infer missing facts.
5. Do not use general world knowledge.
6. Return ONLY valid JSON.

Required JSON format:

{{
    "supported": true,
    "confidence": 0.95,
    "reason": "Brief explanation based only on the evidence."
}}
"""

        try:

            response = self.llm.generate(
                prompt
            )

            return self._parse_verification(
                response
            )

        except Exception as exc:

            return {
                "supported": False,
                "confidence": 0.0,
                "reason": (
                    f"Verification failed: {exc}"
                ),
            }

    # =====================================================
    # JSON PARSER
    # =====================================================

    @staticmethod
    def _parse_verification(
        response: str,
    ) -> dict:
        """
        Parse the verifier's JSON response safely.
        """

        response = response.strip()

        # Remove accidental markdown fences.
        response = re.sub(
            r"^```json\s*",
            "",
            response,
            flags=re.IGNORECASE,
        )

        response = re.sub(
            r"\s*```$",
            "",
            response,
        )

        try:

            data = json.loads(
                response
            )

            supported = bool(
                data.get(
                    "supported",
                    False,
                )
            )

            confidence = float(
                data.get(
                    "confidence",
                    0.0,
                )
            )

            confidence = max(
                0.0,
                min(
                    confidence,
                    1.0,
                ),
            )

            reason = str(
                data.get(
                    "reason",
                    "",
                )
            )

            return {
                "supported": supported,
                "confidence": confidence,
                "reason": reason,
            }

        except Exception:

            return {
                "supported": False,
                "confidence": 0.0,
                "reason": (
                    "Verifier returned invalid JSON."
                ),
            }