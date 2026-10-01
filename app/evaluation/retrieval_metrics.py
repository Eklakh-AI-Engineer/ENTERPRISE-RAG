from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

import numpy as np


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def recall_at_k(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
    k: int | None = None,
) -> float:
    retrieved = _unique(retrieved_ids)
    if k is not None:
        retrieved = retrieved[:k]

    expected = set(expected_ids)
    if not expected:
        return 0.0

    return len(set(retrieved).intersection(expected)) / len(expected)


def precision_at_k(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
    k: int | None = None,
) -> float:
    retrieved = _unique(retrieved_ids)
    if k is not None:
        retrieved = retrieved[:k]

    expected = set(expected_ids)
    if not retrieved:
        return 0.0

    return len(set(retrieved).intersection(expected)) / len(retrieved)


def hit_at_k(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
    k: int | None = None,
) -> float:
    retrieved = _unique(retrieved_ids)
    if k is not None:
        retrieved = retrieved[:k]

    expected = set(expected_ids)
    if not expected:
        return 0.0

    return float(bool(set(retrieved).intersection(expected)))


def reciprocal_rank(
    retrieved_ids: Iterable[str],
    expected_ids: Iterable[str],
) -> float:
    expected = set(expected_ids)

    for rank, item_id in enumerate(retrieved_ids, start=1):
        if item_id in expected:
            return 1.0 / rank

    return 0.0


def mean_reciprocal_rank(
    ranked_results: list[Iterable[str]],
    expected_results: list[Iterable[str]],
) -> float:
    if not ranked_results:
        return 0.0

    pairs = zip(ranked_results, expected_results)
    scores = [
        reciprocal_rank(retrieved, expected)
        for retrieved, expected in pairs
    ]

    return sum(scores) / len(scores)


def dcg_at_k(
    retrieved_ids: Sequence[str],
    relevance: Mapping[str, float],
    k: int,
) -> float:
    """Discounted cumulative gain with graded relevance.

    Uses gain = 2^relevance - 1 and log2(rank + 1) discount.
    """
    score = 0.0

    for rank, item_id in enumerate(retrieved_ids[:k], start=1):
        rel = max(0.0, float(relevance.get(item_id, 0.0)))
        score += (2.0**rel - 1.0) / math.log2(rank + 1)

    return score


def ndcg_at_k(
    retrieved_ids: Sequence[str],
    relevance: Mapping[str, float],
    k: int,
) -> float:
    """Normalized DCG for a graded relevance mapping."""
    if k <= 0:
        return 0.0

    actual = dcg_at_k(retrieved_ids, relevance, k)

    ideal_relevances = sorted(
        (max(0.0, float(value)) for value in relevance.values()),
        reverse=True,
    )[:k]

    ideal = sum(
        (2.0**rel - 1.0) / math.log2(rank + 1)
        for rank, rel in enumerate(ideal_relevances, start=1)
    )

    if ideal == 0.0:
        return 0.0

    return actual / ideal


def bootstrap_mean_ci(
    values: Sequence[float],
    *,
    iterations: int = 10_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict:
    """Percentile bootstrap CI for a mean."""
    values = np.asarray(list(values), dtype=float)

    if values.size == 0:
        return {
            "mean": 0.0,
            "lower": 0.0,
            "upper": 0.0,
            "confidence": confidence,
            "iterations": 0,
        }

    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1.")

    rng = np.random.default_rng(seed)
    samples = rng.choice(
        values,
        size=(iterations, values.size),
        replace=True,
    )
    means = samples.mean(axis=1)

    alpha = (1.0 - confidence) / 2.0
    lower, upper = np.quantile(
        means,
        [alpha, 1.0 - alpha],
    )

    return {
        "mean": float(values.mean()),
        "lower": float(lower),
        "upper": float(upper),
        "confidence": confidence,
        "iterations": iterations,
    }


def paired_bootstrap_delta_ci(
    baseline: Sequence[float],
    treatment: Sequence[float],
    *,
    iterations: int = 10_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict:
    """Paired bootstrap CI for treatment - baseline.

    Pairing preserves the query-level comparison required for a controlled
    Dense-vs-Hybrid experiment.
    """
    baseline = np.asarray(list(baseline), dtype=float)
    treatment = np.asarray(list(treatment), dtype=float)

    if baseline.size != treatment.size:
        raise ValueError("baseline and treatment must have equal length.")

    if baseline.size == 0:
        return {
            "mean_delta": 0.0,
            "lower": 0.0,
            "upper": 0.0,
            "confidence": confidence,
            "iterations": 0,
        }

    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1.")

    deltas = treatment - baseline
    rng = np.random.default_rng(seed)
    samples = rng.choice(
        deltas,
        size=(iterations, deltas.size),
        replace=True,
    )
    means = samples.mean(axis=1)

    alpha = (1.0 - confidence) / 2.0
    lower, upper = np.quantile(
        means,
        [alpha, 1.0 - alpha],
    )

    return {
        "mean_delta": float(deltas.mean()),
        "lower": float(lower),
        "upper": float(upper),
        "confidence": confidence,
        "iterations": iterations,
    }
