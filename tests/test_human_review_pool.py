from scripts import human_review


def test_pool_is_keyed_by_query_and_candidate_index():
    item = human_review.flatten_judgments(human_review.load_silver())[0]
    candidate = human_review.resolve_candidate(item, human_review.load_pool())
    assert candidate["chunk_id"] == "CHA Employee Handbook 2025-p006-c001"
    assert candidate["text"]


def test_missing_candidate_is_reported():
    item = {
        "review_id": "NOPE::0",
        "query_id": "NOPE",
        "candidate_index": 0,
        "chunk_id": "MISSING",
    }
    try:
        human_review.resolve_candidate(item, {})
    except KeyError as error:
        assert "NOPE::0" in str(error)
    else:
        raise AssertionError("Missing candidate should fail resolution")
