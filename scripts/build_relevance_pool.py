#!/usr/bin/env python3
"""Build a Dense ∪ BM25 relevance pool for Phase 2 annotation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.dense.retriever import DenseRetriever


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def candidate_view(item: dict, source: str, rank: int) -> dict:
    text = item.get("text", "")
    return {
        "chunk_id": item.get("chunk_id"),
        "document_id": item.get("document_id") or item.get("document") or item.get("source"),
        "document": item.get("document") or item.get("source"),
        "page": item.get("page"),
        "section": item.get("section"),
        "text": text,
        "start_char": item.get("start_char"),
        "end_char": item.get("end_char"),
        "retrieval_sources": [source],
        "retrieval_ranks": {source: rank},
        "scores": {source: item.get("score")},
    }


def merge_candidate(pool: dict, item: dict, source: str, rank: int) -> None:
    chunk_id = item.get("chunk_id")
    if not chunk_id:
        return

    if chunk_id not in pool:
        pool[chunk_id] = candidate_view(item, source, rank)
        return

    entry = pool[chunk_id]
    if source not in entry["retrieval_sources"]:
        entry["retrieval_sources"].append(source)
    entry["retrieval_ranks"][source] = rank
    entry["scores"][source] = item.get("score")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", default="data/processed/sample_chunks.json")
    parser.add_argument("--queries", required=True)
    parser.add_argument("--output", default="data/evaluation/phase2_pool.json")
    parser.add_argument("--candidate-k", type=int, default=10)
    args = parser.parse_args()

    chunks_payload = load_json(args.chunks)
    queries_payload = load_json(args.queries)

    chunks = (
        chunks_payload["chunks"]
        if isinstance(chunks_payload, dict) and "chunks" in chunks_payload
        else chunks_payload
    )
    queries = (
        queries_payload["queries"]
        if isinstance(queries_payload, dict) and "queries" in queries_payload
        else queries_payload
    )

    if not isinstance(chunks, list) or not isinstance(queries, list):
        raise TypeError("chunks and queries must resolve to lists.")

    dense = DenseRetriever()
    dense.build_index(chunks)

    bm25 = BM25Retriever()
    bm25.build_index(chunks)

    pooled = []

    for item in queries:
        query = item["query"]
        pool = {}

        for rank, result in enumerate(
            dense.search(query, top_k=args.candidate_k), start=1
        ):
            merge_candidate(pool, result, "dense", rank)

        for rank, result in enumerate(
            bm25.search(query, top_k=args.candidate_k), start=1
        ):
            merge_candidate(pool, result, "bm25", rank)

        pooled.append({
            "query_id": item["query_id"],
            "category": item.get("category"),
            "query": query,
            "candidate_count": len(pool),
            "candidates": list(pool.values()),
        })

    payload = {
        "pool_version": "v0.1",
        "pooling_rule": "Dense(query) UNION BM25(query)",
        "candidate_k": args.candidate_k,
        "queries": pooled,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"queries": len(pooled), "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
