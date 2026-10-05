import json
import pytest
from pathlib import Path
import sys

# Ensure the repository root is in sys.path for importing scripts
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "scripts"))

import human_review

def test_load_pool_contains_known_chunk():
    pool_index = human_review.load_pool()
    known_chunk_id = "CHA Employee Handbook 2025-p006-c001"
    assert known_chunk_id in pool_index, f"Chunk ID {known_chunk_id} not found in pool"
    chunk = pool_index[known_chunk_id]
    assert "text" in chunk, "Chunk does not contain 'text' field"
    assert isinstance(chunk["text"], str)
    assert len(chunk["text"]) > 0

def test_load_pool_missing_chunk():
    pool_index = human_review.load_pool()
    assert "NON_EXISTENT_CHUNK_ID" not in pool_index
