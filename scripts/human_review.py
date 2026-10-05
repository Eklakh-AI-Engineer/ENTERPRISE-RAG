import argparse
import json
import tempfile
import os
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_PATH = REPO_ROOT / "data" / "evaluation" / "cha_silver_labels_v1.json"
REVIEW_PATH = REPO_ROOT / "data" / "evaluation" / "cha_human_review_v1.json"
POOL_PATH = REPO_ROOT / "data" / "evaluation" / "cha_pool_v1.json"
REVIEW_SCHEMA_VERSION = "human-review-v1"

SCALE = {
    "0": "Not relevant",
    "1": "Marginal",
    "2": "Relevant",
    "3": "Highly relevant",
}


def make_review_id(query_id: str, candidate_index: int) -> str:
    if not isinstance(query_id, str) or not query_id.strip():
        raise ValueError("query_id must be a non-empty string.")
    if not isinstance(candidate_index, int) or isinstance(candidate_index, bool) or candidate_index < 0:
        raise ValueError("A review ID requires a query_id and non-negative candidate_index.")
    return f"{query_id}::{candidate_index}"


def load_silver(path: Path = SILVER_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_judgments(silver: dict) -> list[dict]:
    items = []
    seen_ids = set()
    for query in silver.get("queries", []):
        for judgment in query.get("judgments", []):
            query_id = query.get("query_id")
            candidate_index = judgment.get("candidate_index")
            review_id = make_review_id(query_id, candidate_index)
            if review_id in seen_ids:
                raise ValueError(f"Duplicate silver review ID: {review_id}")
            seen_ids.add(review_id)
            items.append({
                "review_id": review_id,
                "query_id": query_id,
                "query": query.get("query", ""),
                "candidate_index": candidate_index,
                "chunk_id": judgment.get("chunk_id"),
            })
    return items


def load_pool(path: Path = POOL_PATH) -> dict[tuple[str, int], dict]:
    pool = json.loads(path.read_text(encoding="utf-8"))
    index = {}
    for query in pool.get("queries", []):
        query_id = query.get("query_id")
        for candidate_index, candidate in enumerate(query.get("candidates", [])):
            index[(query_id, candidate_index)] = candidate
    return index


def resolve_candidate(item: dict, pool_index: dict[tuple[str, int], dict]) -> dict:
    key = (item["query_id"], item["candidate_index"])
    candidate = pool_index.get(key)
    if candidate is None:
        raise KeyError(f"Candidate not found in pool: {item['review_id']}")
    if candidate.get("chunk_id") != item.get("chunk_id"):
        raise ValueError(f"Pool chunk ID does not match silver candidate: {item['review_id']}")
    required = ("text", "document_id", "page", "start_char", "end_char")
    missing = [key for key in required if candidate.get(key) is None]
    if missing or not candidate.get("text"):
        raise ValueError(f"Candidate {item['review_id']} has incomplete provenance: {missing}")
    if candidate["end_char"] <= candidate["start_char"]:
        raise ValueError(f"Candidate {item['review_id']} has an invalid character span.")
    return candidate


def load_review(path: Path = REVIEW_PATH) -> dict:
    if not path.is_file():
        return {"schema_version": REVIEW_SCHEMA_VERSION, "reviewed": []}
    review = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(review.get("reviewed", []), list):
        raise ValueError("Review file 'reviewed' field must be an array.")
    return review


def validate_review_record(record: dict) -> None:
    required = (
        "review_id", "query_id", "candidate_index", "chunk_id", "document_id",
        "page", "start_char", "end_char", "human_relevance", "verified", "note",
    )
    missing = [key for key in required if key not in record]
    if missing:
        raise ValueError(f"Human review record is missing fields: {missing}")
    if record["review_id"] != make_review_id(record["query_id"], record["candidate_index"]):
        raise ValueError("review_id must be query_id::candidate_index.")
    if not isinstance(record["chunk_id"], str) or not record["chunk_id"]:
        raise ValueError("chunk_id must be a non-empty string.")
    if not isinstance(record["document_id"], str) or not record["document_id"]:
        raise ValueError("document_id must be a non-empty string.")
    if not isinstance(record["human_relevance"], int) or isinstance(record["human_relevance"], bool) or record["human_relevance"] not in range(4):
        raise ValueError("human_relevance must be an integer from 0 through 3.")
    if not isinstance(record["verified"], bool):
        raise ValueError("verified must be a boolean.")
    if not isinstance(record["page"], int) or isinstance(record["page"], bool) or record["page"] < 1:
        raise ValueError("page must be a positive integer.")
    if (
        not isinstance(record["start_char"], int)
        or isinstance(record["start_char"], bool)
        or not isinstance(record["end_char"], int)
        or isinstance(record["end_char"], bool)
        or record["start_char"] < 0
        or record["end_char"] <= record["start_char"]
    ):
        raise ValueError("The human review character span is invalid.")
    if not isinstance(record["note"], str):
        raise ValueError("note must be a string.")


def review_map(review: dict) -> dict[str, dict]:
    records = {}
    for record in review.get("reviewed", []):
        if not isinstance(record, dict):
            raise ValueError("Every human review row must be an object.")
        if "review_id" not in record:
            continue
        validate_review_record(record)
        review_id = record["review_id"]
        if review_id in records:
            raise ValueError(f"Duplicate human review ID: {review_id}")
        records[review_id] = record
    return records


def save_review(review: dict, path: Path = REVIEW_PATH) -> None:
    records = review_map(review)
    payload = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "reviewed": list(records.values()),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(payload, temp_file, indent=2, ensure_ascii=False)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def make_review_record(item: dict, candidate: dict, human_relevance: int, verified: bool, note: str) -> dict:
    record = {
        "review_id": item["review_id"],
        "query_id": item["query_id"],
        "candidate_index": item["candidate_index"],
        "chunk_id": candidate["chunk_id"],
        "document_id": candidate["document_id"],
        "page": candidate["page"],
        "start_char": candidate["start_char"],
        "end_char": candidate["end_char"],
        "human_relevance": human_relevance,
        "verified": verified,
        "note": note.strip(),
    }
    validate_review_record(record)
    return record


def upsert_review(review: dict, record: dict) -> dict:
    validate_review_record(record)
    records = review_map(review)
    records[record["review_id"]] = record
    return {"schema_version": REVIEW_SCHEMA_VERSION, "reviewed": list(records.values())}


def first_unreviewed_index(items: list[dict], reviewed_ids: set[str]) -> int | None:
    return next((index for index, item in enumerate(items) if item["review_id"] not in reviewed_ids), None)


def display_item(item: dict, candidate: dict, idx: int, total: int, existing_review: dict | None = None, output_fn: Callable[[str], None] = print) -> None:
    print_fn = output_fn
    print_fn(f"--- Review {idx + 1}/{total} ---")
    print_fn(f"Review ID: {item['review_id']}")
    print_fn(f"Query: {item['query']}")
    print_fn(f"Chunk ID: {candidate['chunk_id']}")
    print_fn(f"Document: {candidate.get('document') or candidate['document_id']}")
    print_fn(f"Document ID: {candidate['document_id']}")
    print_fn(f"Page: {candidate['page']}")
    print_fn(f"Character span: [{candidate['start_char']}, {candidate['end_char']})")
    if existing_review is not None:
        print_fn(f"Existing human label: {existing_review['human_relevance']}")
    print_fn("\n--- Candidate text ---")
    print_fn(candidate["text"])
    print_fn("--- End candidate text ---\n")
    print_fn("Human relevance (0-3):")
    for code, description in SCALE.items():
        print_fn(f"  {code} = {description}")
    print_fn("Enter 0-3 to label, n for next, p for previous/edit, q to quit.")


def main(
    review_path: Path = REVIEW_PATH,
    silver_path: Path = SILVER_PATH,
    pool_path: Path = POOL_PATH,
    preview: bool = False,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    items = flatten_judgments(load_silver(silver_path))
    candidates = load_pool(pool_path)
    review = load_review(review_path)
    reviewed = review_map(review)
    total = len(items)
    if not items:
        output_fn("No candidates are available for review.")
        return

    idx = first_unreviewed_index(items, set(reviewed))
    if idx is None:
        idx = total - 1

    if preview:
        item = items[idx]
        candidate = resolve_candidate(item, candidates)
        display_item(item, candidate, idx, total, reviewed.get(item["review_id"]), output_fn)
        output_fn("Preview only; no input accepted and no review data written.")
        return

    while 0 <= idx < total:
        item = items[idx]
        candidate = resolve_candidate(item, candidates)
        display_item(item, candidate, idx, total, reviewed.get(item["review_id"]), output_fn)
        response = input_fn("Your input (0-3 / n / p / q): ").strip().lower()
        if response in SCALE:
            verified_response = input_fn("Is the displayed evidence/provenance verified? (y/n): ").strip().lower()
            while verified_response not in {"y", "n"}:
                output_fn("Enter y or n.")
                verified_response = input_fn("Verified? (y/n): ").strip().lower()
            note = input_fn("Optional note (Enter to skip): ")
            record = make_review_record(item, candidate, int(response), verified_response == "y", note)
            review = upsert_review({"reviewed": list(reviewed.values())}, record)
            save_review(review, review_path)
            reviewed = review_map(review)
            output_fn(f"Saved {record['review_id']}.")
            idx += 1
        elif response == "n":
            idx += 1
        elif response == "p":
            if idx > 0:
                idx -= 1
            else:
                output_fn("Already at the first candidate.")
        elif response == "q":
            output_fn(f"Progress preserved: {len(reviewed)} of {total} candidates labeled.")
            return
        else:
            output_fn("Invalid input. Use 0-3, n, p, or q.")

    output_fn(f"Reached end: {len(reviewed)} of {total} candidates labeled. No benchmark was changed.")


def cli() -> None:
    parser = argparse.ArgumentParser(description="Blind human review of pooled retrieval candidates.")
    parser.add_argument("--review-file", type=Path, default=REVIEW_PATH)
    parser.add_argument("--silver-file", type=Path, default=SILVER_PATH)
    parser.add_argument("--pool-file", type=Path, default=POOL_PATH)
    parser.add_argument("--preview", action="store_true", help="Display the next candidate without accepting input or saving.")
    args = parser.parse_args()
    main(args.review_file, args.silver_file, args.pool_file, preview=args.preview)


if __name__ == "__main__":
    cli()
