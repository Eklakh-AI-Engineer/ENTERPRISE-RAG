from app.evaluation.retrieval_metrics import (
    bootstrap_mean_ci,
    dcg_at_k,
    ndcg_at_k,
    paired_bootstrap_delta_ci,
)


def test_ndcg_perfect_ranking_is_one():
    relevance = {"a": 3, "b": 2, "c": 1}
    assert ndcg_at_k(["a", "b", "c"], relevance, 3) == 1.0


def test_ndcg_penalizes_bad_order():
    relevance = {"a": 3, "b": 0}
    assert ndcg_at_k(["b", "a"], relevance, 2) < 1.0


def test_dcg_ignores_items_without_relevance():
    relevance = {"a": 2}
    assert dcg_at_k(["x", "a"], relevance, 2) > 0.0


def test_bootstrap_mean_ci_is_reproducible():
    values = [0.1, 0.2, 0.3, 0.4]
    first = bootstrap_mean_ci(values, iterations=500, seed=42)
    second = bootstrap_mean_ci(values, iterations=500, seed=42)
    assert first == second
    assert first["mean"] == 0.25


def test_paired_bootstrap_delta_tracks_treatment_minus_baseline():
    baseline = [0.2, 0.4, 0.6]
    treatment = [0.3, 0.5, 0.7]
    result = paired_bootstrap_delta_ci(
        baseline,
        treatment,
        iterations=500,
        seed=42,
    )
    assert result["mean_delta"] == 0.1
