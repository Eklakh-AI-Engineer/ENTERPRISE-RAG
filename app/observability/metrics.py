from dataclasses import dataclass, asdict
from time import perf_counter


@dataclass
class PipelineMetrics:

    # ---------------------------------------------------------
    # Latency
    # ---------------------------------------------------------

    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    generation_ms: float = 0.0
    citation_verification_ms: float = 0.0
    evaluation_ms: float = 0.0
    faithfulness_ms: float = 0.0
    total_ms: float = 0.0

    # ---------------------------------------------------------
    # Retrieval statistics
    # ---------------------------------------------------------

    retrieved_count: int = 0
    reranked_count: int = 0

    # ---------------------------------------------------------
    # Citation quality
    # ---------------------------------------------------------

    citation_validity: float = 0.0
    citation_accuracy: float = 0.0

    total_citations: int = 0
    valid_citations: int = 0
    invalid_citations: int = 0

    # ---------------------------------------------------------
    # Answer quality
    # ---------------------------------------------------------

    relevance_score: float = 0.0

    # ---------------------------------------------------------
    # Faithfulness / evidence grounding
    # ---------------------------------------------------------

    faithfulness_score: float = 0.0

    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: int = 0

    # ---------------------------------------------------------
    # Overall pipeline quality
    # ---------------------------------------------------------

    overall_score: float = 0.0

    # ---------------------------------------------------------
    # Timing helpers
    # ---------------------------------------------------------

    @staticmethod
    def timer():
        """
        Start a high-resolution performance timer.
        """
        return perf_counter()

    @staticmethod
    def elapsed_ms(start: float) -> float:
        """
        Return elapsed time in milliseconds.
        """
        return round(
            (perf_counter() - start) * 1000,
            2,
        )

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Convert metrics into a JSON-serializable dictionary.
        """
        return asdict(self)