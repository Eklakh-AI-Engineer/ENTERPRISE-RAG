import hashlib
import json
import pytest

from scripts import human_review

REPO_ROOT = human_review.REPO_ROOT
SILVER_PATH = REPO_ROOT / "data" / "evaluation" / "cha_silver_labels_v1.json"
GOLDEN_PATH = REPO_ROOT / "data" / "evaluation" / "golden_queries_v1.json"


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_candidate():
    item = human_review.flatten_judgments(human_review.load_silver())[0]
    candidate = human_review.resolve_candidate(item, human_review.load_pool())
    return item, candidate


def make_record(item=None, candidate=None, relevance=2, verified=True, note=""):
    if item is None or candidate is None:
        item, candidate = first_candidate()
    return human_review.make_review_record(item, candidate, relevance, verified, note)


def test_stable_review_id():
    assert human_review.make_review_id("CHA-001", 0) == "CHA-001::0"


def test_exact_chunk_text_and_provenance_resolution():
    item, candidate = first_candidate()
    processed = human_review.REPO_ROOT / "data" / "processed" / "cha_chunks.json"
    chunks = json.loads(processed.read_text(encoding="utf-8"))
    if isinstance(chunks, dict):
        chunks = chunks["chunks"]
    source = next(chunk for chunk in chunks if chunk["chunk_id"] == item["chunk_id"])
    assert candidate["text"] == source["text"]
    for field in ("document_id", "page", "start_char", "end_char"):
        assert candidate[field] == source[field]


def test_blind_display_shows_full_candidate_and_provenance(capsys):
    item, candidate = first_candidate()
    assert not {"relevance", "confidence", "original_relevance", "original_confidence"}.intersection(item)

    human_review.display_item(item, candidate, 0, 1)

    output = capsys.readouterr().out
    assert item["query"] in output
    assert candidate["chunk_id"] in output
    assert candidate["document_id"] in output
    assert f"[{candidate['start_char']}, {candidate['end_char']})" in output
    assert candidate["text"] in output
    assert "AI relevance" not in output
    assert "confidence" not in output.lower()


def test_valid_human_labels_0_through_3():
    item, candidate = first_candidate()
    for relevance in range(4):
        record = make_record(item, candidate, relevance=relevance)
        assert record["human_relevance"] == relevance


@pytest.mark.parametrize("relevance", [-1, 4, True, 1.0])
def test_invalid_human_labels_are_rejected(relevance):
    item, candidate = first_candidate()
    with pytest.raises(ValueError):
        make_record(item, candidate, relevance=relevance)


def test_duplicate_prevention_and_exact_id_replacement():
    original = make_record(relevance=1, note="first")
    edited = make_record(relevance=3, note="edited")
    updated = human_review.upsert_review({"reviewed": [original]}, edited)
    assert len(updated["reviewed"]) == 1
    assert updated["reviewed"][0] == edited

    with pytest.raises(ValueError, match="Duplicate human review ID"):
        human_review.review_map({"reviewed": [original, original]})


def test_resume_uses_arbitrary_review_ids():
    items = human_review.flatten_judgments(human_review.load_silver())
    reviewed_ids = {items[0]["review_id"], items[4]["review_id"]}
    assert human_review.first_unreviewed_index(items, reviewed_ids) == 1


def test_atomic_save_uses_replace(tmp_path, monkeypatch):
    record = make_record()
    review_path = tmp_path / "review.json"
    replaced = []
    actual_replace = human_review.os.replace

    def track_replace(source, destination):
        replaced.append((source, destination))
        actual_replace(source, destination)

    monkeypatch.setattr(human_review.os, "replace", track_replace)
    human_review.save_review({"reviewed": [record]}, review_path)

    saved = human_review.load_review(review_path)
    assert saved["reviewed"] == [record]
    assert len(replaced) == 1
    assert replaced[0][1] == review_path
    assert list(tmp_path.glob("*.tmp")) == []


def test_label_autosaves_q_preserves_progress_and_does_not_freeze_golden(tmp_path):
    review_path = tmp_path / "review.json"
    silver_hash = file_hash(SILVER_PATH)
    golden_hash = file_hash(GOLDEN_PATH)
    responses = iter(["3", "y", "saved before quitting", "q"])

    human_review.main(
        review_path=review_path,
        input_fn=lambda _prompt: next(responses),
        output_fn=lambda _message: None,
    )

    saved = human_review.load_review(review_path)
    assert len(saved["reviewed"]) == 1
    assert saved["reviewed"][0]["human_relevance"] == 3
    assert saved["reviewed"][0]["verified"] is True
    assert saved["reviewed"][0]["note"] == "saved before quitting"
    assert file_hash(SILVER_PATH) == silver_hash
    assert file_hash(GOLDEN_PATH) == golden_hash
    assert json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))["status"] == "draft_pending_human_annotation"


def test_next_does_not_create_a_judgment(tmp_path):
    review_path = tmp_path / "review.json"
    responses = iter(["n", "q"])
    human_review.main(
        review_path=review_path,
        input_fn=lambda _prompt: next(responses),
        output_fn=lambda _message: None,
    )
    assert not review_path.exists()


def test_previous_allows_editing_existing_id(tmp_path):
    review_path = tmp_path / "review.json"
    item, candidate = first_candidate()
    human_review.save_review({"reviewed": [make_record(item, candidate, relevance=0)]}, review_path)
    responses = iter(["p", "1", "y", "corrected", "q"])

    human_review.main(
        review_path=review_path,
        input_fn=lambda _prompt: next(responses),
        output_fn=lambda _message: None,
    )

    saved = human_review.load_review(review_path)["reviewed"]
    assert len(saved) == 1
    assert saved[0]["review_id"] == item["review_id"]
    assert saved[0]["human_relevance"] == 1
    assert saved[0]["note"] == "corrected"


def test_preview_does_not_modify_silver_or_tracked_review(tmp_path):
    silver_hash = file_hash(SILVER_PATH)
    review_hash = file_hash(human_review.REVIEW_PATH)
    preview_path = tmp_path / "review.json"
    human_review.main(review_path=preview_path, preview=True, output_fn=lambda _message: None)
    assert not preview_path.exists()
    assert file_hash(SILVER_PATH) == silver_hash
    assert file_hash(human_review.REVIEW_PATH) == review_hash
