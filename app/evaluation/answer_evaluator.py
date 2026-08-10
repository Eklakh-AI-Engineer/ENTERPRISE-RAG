import re


class AnswerEvaluator:
    """
    Evaluates a generated RAG answer using:

    - citation presence
    - citation validity
    - citation coverage
    - answer relevance
    """

    # IMPORTANT:
    # The square brackets must be escaped.
    #
    # Correct:
    #   [Source 1]
    #
    # Regex:
    #   \[Source\s+(\d+)\]
    SOURCE_PATTERN = re.compile(
        r"\[Source\s+(\d+)\]",
        re.IGNORECASE,
    )

    def evaluate(
        self,
        query: str,
        answer: str,
        context_sources: list[dict],
    ) -> dict:
        """
        Evaluate the generated answer against
        the retrieved context sources.
        """

        source_ids = self._extract_source_ids(
            answer
        )

        # Valid source numbers are 1..N.
        valid_source_ids = {
            i
            for i in range(
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

        # -------------------------------------------------
        # Citation score
        # -------------------------------------------------

        if source_ids:
            citation_score = (
                len(valid_citations)
                / len(source_ids)
            )
        else:
            citation_score = 0.0

        # -------------------------------------------------
        # Citation accuracy
        # -------------------------------------------------

        if source_ids:
            citation_accuracy = (
                len(valid_citations)
                / len(source_ids)
            )
        else:
            citation_accuracy = 0.0

        # -------------------------------------------------
        # Answer relevance
        # -------------------------------------------------

        relevance_score = self._calculate_relevance(
            query=query,
            answer=answer,
        )

        # -------------------------------------------------
        # Evidence support
        # -------------------------------------------------

        support_score = self._calculate_support(
            answer=answer,
            source_ids=source_ids,
            valid_source_ids=valid_source_ids,
        )

        # -------------------------------------------------
        # Overall score
        # -------------------------------------------------

        overall_score = (
            0.4 * citation_score
            + 0.3 * relevance_score
            + 0.3 * support_score
        )

        # -------------------------------------------------
        # Result
        # -------------------------------------------------

        return {
            "query": query,

            "citation_score": round(
                citation_score,
                4,
            ),

            "citation_accuracy": round(
                citation_accuracy,
                4,
            ),

            "relevance_score": round(
                relevance_score,
                4,
            ),

            "support_score": round(
                support_score,
                4,
            ),

            "overall_score": round(
                overall_score,
                4,
            ),

            "total_citations": len(
                source_ids
            ),

            "valid_citations": valid_citations,

            "invalid_citations": invalid_citations,

            "supported_claims": len(
                valid_citations
            ),

            "unsupported_claims": max(
                len(source_ids)
                - len(valid_citations),
                0,
            ),

            "passed": (
                overall_score >= 0.75
                and len(invalid_citations) == 0
            ),
        }

    # -----------------------------------------------------
    # Citation extraction
    # -----------------------------------------------------

    def _extract_source_ids(
        self,
        answer: str,
    ) -> list[int]:
        """
        Extract unique [Source N] citations.
        """

        matches = self.SOURCE_PATTERN.findall(
            answer
        )

        source_ids = []

        for match in matches:

            source_id = int(match)

            if source_id not in source_ids:
                source_ids.append(
                    source_id
                )

        return source_ids

    # -----------------------------------------------------
    # Relevance
    # -----------------------------------------------------

    def _calculate_relevance(
        self,
        query: str,
        answer: str,
    ) -> float:
        """
        Lightweight deterministic lexical
        relevance score.

        This does not require another LLM call.
        """

        query_words = set(
            self._tokenize(query)
        )

        answer_words = set(
            self._tokenize(answer)
        )

        if not query_words:
            return 0.0

        overlap = query_words.intersection(
            answer_words
        )

        return min(
            len(overlap)
            / len(query_words),
            1.0,
        )

    # -----------------------------------------------------
    # Evidence support
    # -----------------------------------------------------

    def _calculate_support(
        self,
        answer: str,
        source_ids: list[int],
        valid_source_ids: set[int],
    ) -> float:
        """
        Estimate evidence support using citation validity.

        An answer without citations is treated as
        unsupported.

        NOTE:
        This checks citation validity, not semantic
        entailment between claims and source text.
        """

        if not answer.strip():
            return 0.0

        if not source_ids:
            return 0.0

        valid_count = sum(
            1
            for source_id in source_ids
            if source_id in valid_source_ids
        )

        return min(
            valid_count
            / len(source_ids),
            1.0,
        )

    # -----------------------------------------------------
    # Tokenizer
    # -----------------------------------------------------

    @staticmethod
    def _tokenize(
        text: str,
    ) -> list[str]:

        return re.findall(
            r"\b[a-zA-Z0-9]+\b",
            text.lower(),
        )