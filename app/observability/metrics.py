from dataclasses import dataclass, asdict
from time import perf_counter


@dataclass
class PipelineMetrics:
    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    generation_ms: float = 0.0
    evaluation_ms: float = 0.0
    total_ms: float = 0.0

    retrieved_count: int = 0
    reranked_count: int = 0

    citation_score: float = 0.0
    relevance_score: float = 0.0
    support_score: float = 0.0
    overall_score: float = 0.0

    @staticmethod
    def timer():
        return perf_counter()

    @staticmethod
    def elapsed_ms(start: float) -> float:
        return round((perf_counter() - start) * 1000, 2)

    def to_dict(self) -> dict:
        return asdict(self)