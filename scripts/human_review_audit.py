import json
from pathlib import Path
from collections import Counter, defaultdict

# Paths (relative to repository root)
REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_PATH = REPO_ROOT / "data" / "evaluation" / "cha_silver_labels_v1.json"
REVIEW_PATH = REPO_ROOT / "data" / "evaluation" / "cha_human_review_v1.json"

def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def compute_stats():
    silver = load_json(SILVER_PATH)
    review = load_json(REVIEW_PATH) if REVIEW_PATH.is_file() else {"reviewed": []}
    total = sum(len(q.get("judgments", [])) for q in silver.get("queries", []))
    reviewed = review.get("reviewed", [])
    reviewed_count = len(reviewed)
    remaining = total - reviewed_count

    # Build map of AI relevance per (query_id, candidate_index)
    ai_map = {}
    ai_dist = Counter()
    for q in silver.get("queries", []):
        qid = q.get("query_id")
        for j in q.get("judgments", []):
            key = (qid, j.get("candidate_index"))
            rel = j.get("relevance")
            ai_map[key] = rel
            ai_dist[rel] += 1

    human_dist = Counter()
    agreement = 0
    confusion = defaultdict(Counter)
    query_disagree = Counter()

    for entry in reviewed:
        key = (entry["query_id"], entry["candidate_index"])
        ai_rel = ai_map.get(key)
        human_rel = entry.get("human_relevance")
        human_dist[human_rel] += 1
        confusion[ai_rel][human_rel] += 1
        if ai_rel == human_rel:
            agreement += 1
        else:
            query_disagree[entry["query_id"]] += 1

    agreement_pct = (agreement / reviewed_count * 100) if reviewed_count else 0.0

    print(f"Total judgments (silver): {total}")
    print(f"Reviewed judgments: {reviewed_count}")
    print(f"Remaining: {remaining}\n")
    print(f"AI relevance distribution: {dict(ai_dist)}")
    print(f"Human relevance distribution: {dict(human_dist)}\n")
    print(f"Agreement: {agreement}/{reviewed_count} ({agreement_pct:.2f}%)\n")
    print("Confusion matrix (AI \u2192 Human):")
    for ai_rel in sorted(confusion.keys()):
        row = {human: confusion[ai_rel][human] for human in range(4)}
        print(f" AI {ai_rel}: {row}")
    print("\nTop 5 queries with most disagreements:")
    for qid, cnt in query_disagree.most_common(5):
        print(f" {qid}: {cnt} mismatches")

if __name__ == "__main__":
    compute_stats()
