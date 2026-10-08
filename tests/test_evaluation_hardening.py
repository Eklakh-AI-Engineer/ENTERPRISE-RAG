import json

from scripts.evaluate_answerability import is_insufficient_evidence
from scripts.evaluate_faithfulness_judge import cohens_kappa


def test_cohens_kappa_perfect_agreement():
    assert cohens_kappa([True, False, True, False], [True, False, True, False]) == 1.0


def test_cohens_kappa_detects_chance_adjusted_disagreement():
    value = cohens_kappa([True, True, False, False], [True, False, True, False])
    assert value < 1.0


def test_insufficient_evidence_phrase_detection():
    assert is_insufficient_evidence(
        "I don't have enough information in the provided documents to answer this."
    )
    assert not is_insufficient_evidence(
        "The supplied evidence directly states the policy requirement."
    )


def test_challenge_set_contract():
    with open("data/evaluation/challenge_queries_v1.json", encoding="utf-8") as f:
        payload = json.load(f)
    assert len(payload["queries"]) == 20
    assert sum(q["challenge_type"] == "unanswerable" for q in payload["queries"]) == 10
    assert sum(q["challenge_type"] == "hard_in_domain" for q in payload["queries"]) == 10
