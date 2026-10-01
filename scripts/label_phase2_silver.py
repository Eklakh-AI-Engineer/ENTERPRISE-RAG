#!/usr/bin/env python3
"""Generate silver relevance judgments for the Phase 2 retrieval pool."""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
from typing import Any
import requests

PROMPT_VERSION = "phase2-relevance-silver-v1"
LABELS = {0, 1, 2, 3}

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)

def call_model(api_key: str, model: str, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    system = """You are a retrieval-evaluation judge.
Assign relevance to each evidence chunk for the query.
0 = not relevant.
1 = marginal: related topic but little useful evidence.
2 = relevant: useful evidence but incomplete or indirect.
3 = highly relevant: direct, specific evidence that can answer or strongly support the query.
Judge independently. Do not reward keyword overlap alone.
Return JSON only:
{"judgments":[{"candidate_index":0,"relevance":0,"confidence":0.0}]}
Confidence must be between 0 and 1."""
    user = {
        "query": query,
        "candidates": [
            {"candidate_index": i, "text": c["text"], "document": c.get("document"),
             "page": c.get("page"), "section": c.get("section")}
            for i, c in enumerate(candidates)
        ],
    }
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Eklakh-AI-Engineer/ENTERPRISE-RAG",
            "X-Title": "Enterprise RAG Phase 2 Silver Labeling",
        },
        json={
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        },
        timeout=120,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    judgments = json.loads(content).get("judgments", [])
    if len(judgments) != len(candidates):
        raise ValueError(f"Expected {len(candidates)} judgments, got {len(judgments)}")
    out = []
    for judgment in judgments:
        idx = int(judgment["candidate_index"])
        relevance = int(judgment["relevance"])
        confidence = float(judgment.get("confidence", 0.0))
        if idx < 0 or idx >= len(candidates) or relevance not in LABELS:
            raise ValueError(f"Invalid judgment: {judgment}")
        out.append({
            "candidate_index": idx,
            "relevance": relevance,
            "confidence": max(0.0, min(1.0, confidence)),
        })
    return sorted(out, key=lambda x: x["candidate_index"])

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=os.getenv("OPENROUTER_MODEL", "qwen/qwen3.8-27b:free"))
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required; no labels were generated.")

    pool = load_json(args.pool)
    existing = load_json(args.output) if args.output.exists() else {
        "schema_version": "phase2-silver-v1",
        "label_source": "silver_ai",
        "prompt_version": PROMPT_VERSION,
        "model": args.model,
        "pool_file": str(args.pool),
        "queries": [],
    }
    done = {q["query_id"]: q for q in existing.get("queries", [])}

    for qi, query in enumerate(pool["queries"], start=1):
        if query["query_id"] in done:
            continue
        judgments = []
        candidates = query["candidates"]
        for start in range(0, len(candidates), args.batch_size):
            batch = candidates[start:start + args.batch_size]
            for attempt in range(args.retries + 1):
                try:
                    batch_judgments = call_model(api_key, args.model, query["query"], batch)
                    judgments.extend([{**j, "candidate_index": j["candidate_index"] + start} for j in batch_judgments])
                    break
                except Exception as exc:
                    if attempt >= args.retries:
                        raise
                    wait = min(30.0, 2.0 ** attempt)
                    print(f"Retrying {query['query_id']} batch {start}:{start + len(batch)} after error: {exc}; waiting {wait:.1f}s")
                    time.sleep(wait)
            time.sleep(args.delay)
        if len(judgments) != len(candidates):
            raise ValueError(f"Expected {len(candidates)} total judgments, got {len(judgments)}")
        records = []
        for judgment in judgments:
            candidate = query["candidates"][judgment["candidate_index"]]
            records.append({
                "candidate_index": judgment["candidate_index"],
                "chunk_id": candidate["chunk_id"],
                "relevance": judgment["relevance"],
                "confidence": judgment["confidence"],
                "label_source": "silver_ai",
            })
        done[query["query_id"]] = {
            "query_id": query["query_id"],
            "category": query["category"],
            "query": query["query"],
            "candidate_count": query["candidate_count"],
            "judgments": records,
        }
        existing["queries"] = [done[key] for key in sorted(done)]
        existing["completed_queries"] = len(done)
        existing["total_queries"] = len(pool["queries"])
        save_json(args.output, existing)
        print("[{}/{}] {} labeled".format(qi, len(pool["queries"]), query["query_id"]))
        time.sleep(args.delay)

if __name__ == "__main__":
    main()
