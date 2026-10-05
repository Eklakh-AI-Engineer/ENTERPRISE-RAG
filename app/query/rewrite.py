from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class QueryRewriteResult:
    original_query: str
    rewritten_query: str
    enabled: bool

    @property
    def changed(self) -> bool:
        return self.rewritten_query != self.original_query


class QueryRewriter:
    """Controlled, deterministic query rewriting.

    The rewrite only removes a leading interrogative frame. The remaining query
    text, including case, identifiers, constraints, and punctuation, is preserved.
    """

    STRATEGY = "strip-interrogative-prefix-v1"
    PREFIX = re.compile(
        r"^(?:(?:please\s+)?(?:can|could) you tell me\s+|"
        r"what\s+(?:does|do|is|are|can)\s+|"
        r"how\s+(?:does|do|should|can)\s+|"
        r"what happens (?:when|if)\s+)",
        re.IGNORECASE,
    )

    def __init__(self, *, enabled: bool = False):
        self.enabled = enabled

    @staticmethod
    def _normalize(query: str) -> str:
        return " ".join((query or "").strip().split())

    def rewrite(self, query: str) -> str:
        normalized = self._normalize(query)
        if not normalized:
            return ""
        if not self.enabled:
            return normalized

        rewritten = self.PREFIX.sub("", normalized, count=1)
        return rewritten.strip() or normalized

    def as_result(self, query: str) -> QueryRewriteResult:
        rewritten = self.rewrite(query)
        return QueryRewriteResult(
            original_query=self._normalize(query),
            rewritten_query=rewritten,
            enabled=self.enabled,
        )
