import re


class AnswerEvaluator:
    """
    Evaluates a generated RAG answer using:
    - citation presence
    - citation validity
    - unsupported claim detection
    - answer relevance
    """

    SOURCE_PATTERN = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)

    def evaluate(
        self,
        query: str,
        answer: str,
        context_sources: list[dict],
    ) -> dict:
        source_ids = self._extract_source_ids(answer)

        valid_source_ids = {
            i for i in range(1, len(context_sources) + 1)
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

        citation_score = (
            len(valid_citations) / len(source_ids)
            if source_ids
            else 0.0
        )

        relevance_score = self._calculate_relevance(
            query,
            answer,
        )

        unsupported_claim_score = self._calculate_support(
            answer,
            source_ids,
            valid_source_ids,
        )

        overall_score = (
            0.4 * citation_score
            + 0.3 * relevance_score
            + 0.3 * unsupported_claim_score
        )

        return {
            "query": query,
            "citation_score": round(citation_score, 4),
            "relevance_score": round(relevance_score, 4),
            "support_score": round(
                unsupported_claim_score,
                4,
            ),
            "overall_score": round(
                overall_score,
                4,
            ),
            "total_citations": len(source_ids),
            "valid_citations": valid_citations,
            "invalid_citations": invalid_citations,
            "passed": (
                overall_score >= 0.75
                and len(invalid_citations) == 0
            ),
        }

    def _extract_source_ids(self, answer: str) -> list[int]:
        matches = self.SOURCE_PATTERN.findall(answer)

        source_ids = []

        for match in matches:
            source_id = int(match)

            if source_id not in source_ids:
                source_ids.append(source_id)

        return source_ids

    def _calculate_relevance(
        self,
        query: str,
        answer: str,
    ) -> float:
        """
        Lightweight lexical relevance score.

        This is intentionally deterministic and does not
        require another LLM call.
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
            len(overlap) / len(query_words),
            1.0,
        )

    def _calculate_support(
        self,
        answer: str,
        source_ids: list[int],
        valid_source_ids: set[int],
    ) -> float:
        """
        Estimate support quality using citation coverage.

        A factual answer without citations is treated as
        unsupported by this evaluator.
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
            valid_count / len(source_ids),
            1.0,
        )

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(
            r"\b[a-zA-Z0-9]+\b",
            text.lower(),
        )