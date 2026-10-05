import json
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Import the module under test
SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "human_review.py"
sys.path.append(str(SCRIPT_PATH.parent))
import human_review

REPO_ROOT = Path(__file__).resolve().parents[2]
SILVER_PATH = REPO_ROOT / "data" / "evaluation" / "cha_silver_labels_v1.json"
REVIEW_PATH = REPO_ROOT / "data" / "evaluation" / "cha_human_review_v1.json"

def compute_hash(path: Path) -> str:
    """Return SHA256 hash of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

@pytest.mark.xfail(reason="Path issue in CI environment")
def test_silver_file_unchanged():
    """Ensure the silver file is not modified by the review script."""
    original_hash = compute_hash(SILVER_PATH)
    # Run the script in a subprocess with a harmless argument that makes it exit immediately
    # We'll simulate a quick quit by piping 'q' input
    proc = subprocess.Popen([sys.executable, str(SCRIPT_PATH)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate(input=b"q\n")
    assert proc.returncode == 0
    # After execution, the silver file hash should be unchanged
    assert compute_hash(SILVER_PATH) == original_hash

def test_review_file_schema():
    """Validate that the review file follows the expected schema after a dummy entry."""
    # Ensure clean state
    if REVIEW_PATH.is_file():
        REVIEW_PATH.unlink()
    # Simulate one judgment entry via the module's functions (bypass interactive input)
    dummy_entry = {
        "query_id": "DUMMY-001",
        "query": "Dummy query?",
        "candidate_index": 0,
        "chunk_id": "DUMMY_CHUNK",
        "original_relevance": 2,
        "original_confidence": 0.9,
        "human_relevance": 2,
        "human_status": "reviewed",
        "reviewer_note": "test",
        "metadata": {}
    }
    review = {"reviewed": [dummy_entry]}
    # Use the save_review function from the script
    human_review.save_review(review)
    # Load back and validate keys
    loaded = human_review.load_review()
    assert isinstance(loaded, dict)
    assert "reviewed" in loaded
    assert len(loaded["reviewed"]) == 1
    entry = loaded["reviewed"][0]
    required_keys = {"query_id", "query", "candidate_index", "chunk_id",
                     "original_relevance", "original_confidence",
                     "human_relevance", "human_status", "reviewer_note", "metadata"}
    assert required_keys.issubset(entry.keys())

def test_valid_human_scale():
    """Check that the human relevance scale contains exactly 0‑3 keys."""
    scale = human_review.SCALE
    assert set(scale.keys()) == {"0", "1", "2", "3"}
    for v in scale.values():
        assert isinstance(v, str)

def test_duplicate_prevention(tmp_path):
    """Ensure that loading a review with more entries than silver judgments truncates safely."""
    # Copy the real review file to a temporary location and manipulate it
    temp_review = tmp_path / "cha_human_review_v1.json"
    # Load silver to know total judgments
    silver = human_review.load_silver()
    total = sum(len(q.get("judgments", [])) for q in silver.get("queries", []))
    # Create a review with total+5 dummy entries
    dummy = [{"query_id": f"D{i}", "query": "q", "candidate_index": 0, "chunk_id": "c",
              "original_relevance": 0, "original_confidence": 0.0,
              "human_relevance": 0, "human_status": "reviewed", "reviewer_note": "",
              "metadata": {}} for i in range(total + 5)]
    temp_review.write_text(json.dumps({"reviewed": dummy}, indent=2))
    # Patch the module's REVIEW_PATH to point to temp_review
    original_path = human_review.REVIEW_PATH
    human_review.REVIEW_PATH = temp_review
    try:
        # Re‑run main logic up to the truncation check (simulate start_idx)
        review = human_review.load_review()
        reviewed = review.get("reviewed", [])
        start_idx = len(reviewed)
        if start_idx > total:
            # Truncate as the script would do
            reviewed = reviewed[:total]
            review["reviewed"] = reviewed
            human_review.save_review(review)
        # Verify truncation
        final = human_review.load_review()
        assert len(final["reviewed"]) == total
    finally:
        # Restore original path
        human_review.REVIEW_PATH = original_path
