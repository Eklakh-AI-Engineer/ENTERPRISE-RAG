from __future__ import annotations

from typing import Iterable


def recall_at_k(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
) -> float:
    retrieved = set(retrieved_ids)
    expected = set(expected_ids)

    if not expected:
        return 0.0

    return len(retrieved.intersection(expected)) / len(expected)


def precision_at_k(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
) -> float:
    retrieved = list(dict.fromkeys(retrieved_ids))
    expected = set(expected_ids)

    if not retrieved:
        return 0.0

    return len(set(retrieved).intersection(expected)) / len(retrieved)


def hit_at_k(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
) -> float:
    retrieved = set(retrieved_ids)
    expected = set(expected_ids)

    if not expected:
        return 0.0

    return float(bool(retrieved.intersection(expected)))


def reciprocal_rank(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
) -> float:
    expected = set(expected_ids)

    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in expected:
            return 1.0 / rank

    return 0.0


def mean_reciprocal_rank(
    ranked_results: list[Iterable[str]],
    expected_results: list[Iterable[str]],
) -> float:
    if not ranked_results:
        return 0.0

    scores = [
        reciprocal_rank(retrieved, expected)
        for retrieved, expected
        in zip(ranked_results, expected_results)
    ]

    return sum(scores) / len(scores)