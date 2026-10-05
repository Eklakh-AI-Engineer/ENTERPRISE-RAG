import json
import os
from pathlib import Path

# Repository root (one level up from this script's directory)
REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_PATH = REPO_ROOT / "data" / "evaluation" / "cha_silver_labels_v1.json"
REVIEW_PATH = REPO_ROOT / "data" / "evaluation" / "cha_human_review_v1.json"

# Load pool file path from silver JSON (default if not present)
POOL_PATH = REPO_ROOT / "data" / "evaluation" / "cha_pool_v1.json"


# Human relevance scale mapping
SCALE = {
    "0": "Not relevant",
    "1": "Marginal",
    "2": "Relevant",
    "3": "Highly relevant",
}

def load_silver() -> dict:
    """Load the silver‑label JSON file."""
    with open(SILVER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def flatten_judgments(silver: dict) -> list:
    """Flatten nested judgments into a flat list for sequential review.

    Each entry preserves the original AI judgment and any extra metadata
    (e.g., document, page/section) that may be present in the judgment object.
    """
    flat = []
    for query in silver.get("queries", []):
        qid = query.get("query_id")
        qtext = query.get("query")
        for judgment in query.get("judgments", []):
            flat.append({
                "query_id": qid,
                "query": qtext,
                "candidate_index": judgment.get("candidate_index"),
                "chunk_id": judgment.get("chunk_id"),
                "original_relevance": judgment.get("relevance"),
                "original_confidence": judgment.get("confidence"),
                # Preserve any extra metadata (document, page, etc.)
                "metadata": {k: v for k, v in judgment.items() if k not in ["candidate_index", "chunk_id", "relevance", "confidence", "label_source"]},
            })
    return flat

def load_review() -> dict:
    """Load the human‑review JSON file, creating an empty structure if missing."""
    if REVIEW_PATH.is_file():
        with open(REVIEW_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {"reviewed": []}

def save_review(review: dict) -> None:
    """Write the review file safely."""
    with open(REVIEW_PATH, "w", encoding="utf-8") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)

def display_item(item: dict, chunk_info: dict, idx: int, total: int) -> None:
    """Render the current judgment for the reviewer, including full chunk evidence."""
    print(f"--- Review {idx + 1}/{total} ---")
    print(f"Query ID : {item['query_id']}")
    print(f"Query    : {item['query']}")
    print(f"Candidate #{item['candidate_index']} (Chunk ID: {item['chunk_id']})")
    # Show metadata from pool if available
    if chunk_info:
        doc = chunk_info.get('document') or chunk_info.get('document_id')
        if doc:
            print(f"Document : {doc}")
        page = chunk_info.get('page')
        if page is not None:
            print(f"Page     : {page}")
        section = chunk_info.get('section')
        if section:
            print(f"Section  : {section}")
        text = chunk_info.get('text')
        if text:
            print("\n--- Evidence ---")
            print(text)
            print("--- End Evidence ---\n")
    else:
        print("[ERROR] Chunk ID not found in pool!")
    # Original AI judgment
    print(f"AI relevance  : {item['original_relevance']} (confidence {item['original_confidence']:.2f})")
    # Any extra metadata from silver judgment
    if item["metadata"]:
        for k, v in item["metadata"].items():
            print(f"{k}: {v}")
    print("Human relevance (0‑3) ?")
    for code, desc in SCALE.items():
        print(f"  {code} = {desc}")
    print("Keyboard shortcuts: 0/1/2/3 to label, n = next, p = previous, q = quit")

def load_pool() -> dict:
    """Load the candidate pool JSON and build an index by chunk_id."""
    if not POOL_PATH.is_file():
        raise FileNotFoundError(f"Pool file not found at {POOL_PATH}")
    with open(POOL_PATH, "r", encoding="utf-8") as f:
        pool = json.load(f)
    # Build dict mapping chunk_id -> candidate dict
    index = {}
    for query in pool.get("queries", []):
        for cand in query.get("candidates", []):
            cid = cand.get("chunk_id")
            if cid:
                index[cid] = cand
    return index


def main() -> None:
    silver = load_silver()
    flat = flatten_judgments(silver)
    total = len(flat)
    review = load_review()
    reviewed = review.get("reviewed", [])
    # Load pool index once
    chunk_index = load_pool()

    # Determine where to resume based on how many judgments are already saved
    start_idx = len(reviewed)
    if start_idx > total:
        print("Warning: review file has more entries than silver judgments. Truncating.")
        reviewed = reviewed[:total]
        start_idx = total
        review["reviewed"] = reviewed
        save_review(review)

    idx = start_idx
    while idx < total:
        item = flat[idx]
        chunk_info = chunk_index.get(item["chunk_id"])
        if not chunk_info:
            print(f"[ERROR] Chunk ID {item['chunk_id']} not found in pool. Aborting.")
            break
        display_item(item, chunk_info, idx, total)
        user_input = input("Your input (0‑3 / n / p / q): ").strip().lower()
        if user_input in {"0", "1", "2", "3"}:
            human_rel = int(user_input)
            note = input("Optional note (Enter to skip): ").strip()
            entry = {
                "query_id": item["query_id"],
                "query": item["query"],
                "candidate_index": item["candidate_index"],
                "chunk_id": item["chunk_id"],
                "original_relevance": item["original_relevance"],
                "original_confidence": item["original_confidence"],
                "human_relevance": human_rel,
                "human_status": "reviewed",
                "reviewer_note": note,
                "metadata": item["metadata"],
            }
            reviewed.append(entry)
            review["reviewed"] = reviewed
            save_review(review)
            print(f"Saved judgment {idx + 1}/{total}.")
            idx += 1
        elif user_input == "n":
            idx += 1
        elif user_input == "p":
            if idx > 0:
                idx -= 1
                if len(reviewed) > idx:
                    reviewed = reviewed[:idx]
                    review["reviewed"] = reviewed
                    save_review(review)
            else:
                print("Already at the first item.")
        elif user_input == "q":
            print("Exiting reviewer – progress saved.")
            break
        else:
            print("Invalid input. Use 0‑3, n, p, or q.")
    if idx >= total:
        print(f"All {total} judgments reviewed! Review saved at {REVIEW_PATH}")

if __name__ == "__main__":
    main()
