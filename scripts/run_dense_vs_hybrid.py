#!/usr/bin/env python3
"""Run the controlled Phase 2 Dense-vs-Hybrid retrieval experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

from app.evaluation.retrieval_metrics import (
    bootstrap_mean_ci,
    ndcg_at_k,
    paired_bootstrap_delta_ci,
    recall_at_k,
    reciprocal_rank,
)
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.hybrid.retriever import HybridRetriever


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_document_id(item: dict) -> str | None:
    return item.get("document_id") or item.get("document") or item.get("source")


def span_overlap(a_start, a_end, b_start, b_end) -> bool:
    if None in (a_start, a_end, b_start, b_end):
        return False
    return max(int(a_start), int(b_start)) < min(int(a_end), int(b_end))


def chunk_relevance(chunk: dict, judgments: list[dict]) -> float:
    chunk_document = normalize_document_id(chunk)
    chunk_page = chunk.get("page")
    chunk_start = chunk.get("start_char")
    chunk_end = chunk.get("end_char")
    chunk_id = chunk.get("chunk_id")

    best = 0.0

    for judgment in judgments:
        if judgment.get("document_id") != chunk_document:
            continue

        if judgment.get("page") != chunk_page:
            continue

        if span_overlap(
            chunk_start,
            chunk_end,
            judgment.get("start_char"),
            judgment.get("end_char"),
        ):
            best = max(best, float(judgment.get("relevance", 0.0)))
            continue

        # Transitional fallback for legacy benchmark records.
        if judgment.get("chunk_id") and judgment.get("chunk_id") == chunk_id:
            best = max(best, float(judgment.get("relevance", 0.0)))

    return best


def judgment_matches_chunk(chunk: dict, judgment: dict) -> bool:
    if judgment.get("document_id") != normalize_document_id(chunk):
        return False
    if judgment.get("page") != chunk.get("page"):
        return False

    if span_overlap(
        chunk.get("start_char"),
        chunk.get("end_char"),
        judgment.get("start_char"),
        judgment.get("end_char"),
    ):
        return True

    return bool(
        judgment.get("chunk_id")
        and judgment.get("chunk_id") == chunk.get("chunk_id")
    )


def evaluate_ranked(\n    results: list[dict],\n    judgments: list[dict],\n    all_chunks: list[dict],\n) -> dict:
    ranked = [
        item for item in results
        if item.get("chunk_id")
    ]

    ranked_ids = [item["chunk_id"] for item in ranked]
    relevance = {}

    for item in all_chunks:
        if not item.get("chunk_id"):
            continue
        relevance[item["chunk_id"]] = max(
            (
                float(judgment.get("relevance", 0.0))
                for judgment in judgments
                if judgment_matches_chunk(item, judgment)
            ),
            default=0.0,
        )

    positive_judgments = [
        judgment
        for judgment in judgments
        if float(judgment.get("relevance", 0.0)) > 0
    ]

    covered = set()
    for item in ranked[:10]:
        for index, judgment in enumerate(positive_judgments):
            if judgment_matches_chunk(item, judgment):
                covered.add(index)

    def recall_for_k(k: int) -> float:
        if not positive_judgments:
            return 0.0
        covered_at_k = set()
        for item in ranked[:k]:
            for index, judgment in enumerate(positive_judgments):
                if judgment_matches_chunk(item, judgment):
                    covered_at_k.add(index)
        return len(covered_at_k) / len(positive_judgments)

    return {
        "recall_at_5": recall_for_k(5),
        "recall_at_10": recall_for_k(10),
        "mrr": next(
            (
                1.0 / rank
                for rank, item in enumerate(ranked, start=1)
                if relevance.get(item["chunk_id"], 0.0) > 0
            ),
            0.0,
        ),
        "ndcg_at_5": ndcg_at_k(ranked_ids, relevance, 5),
        "ndcg_at_10": ndcg_at_k(ranked_ids, relevance, 10),
        "candidate_count": len(ranked),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", default="data/processed/sample_chunks.json")
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--output", default="data/evaluation/phase2_dense_vs_hybrid.json")
    parser.add_argument("--candidate-k", type=int, default=10)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--bootstrap-iterations", type=int, default=10000)
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark)
    benchmark = load_json(args.benchmark)
    chunks = load_json(args.chunks)

    queries = benchmark["queries"]
    if len(queries) < 50:
        raise ValueError(
            f"Phase 2 requires 50–100 labeled queries; received {len(queries)}."
        )
    if len(queries) > 100:
        raise ValueError(
            f"Phase 2 requires 50–100 labeled queries; received {len(queries)}."
        )

    dense = DenseRetriever()
    dense.build_index(chunks)

    bm25 = BM25Retriever()
    bm25.build_index(chunks)

    hybrid = HybridRetriever(dense, bm25)

    per_query = []

    for item in queries:
        query = item["query"]
        judgments = item["relevance"]

        start = time.perf_counter()
        dense_results = dense.search(query, top_k=args.top_k)
        dense_ms = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        hybrid_results = hybrid.search(
            query,
            top_k=args.top_k,
            candidate_k=args.candidate_k,
        )
        hybrid_ms = (time.perf_counter() - start) * 1000

        # For controlled graded nDCG, map durable span judgments to retrieved
        # chunks. Production benchmark records should carry span offsets.
        dense_metrics = evaluate_ranked(dense_results, judgments, chunks)
        hybrid_metrics = evaluate_ranked(hybrid_results, judgments, chunks)

        dense_metrics["retrieval_latency_ms"] = round(dense_ms, 2)
        hybrid_metrics["retrieval_latency_ms"] = round(hybrid_ms, 2)

        per_query.append({
            "query_id": item["query_id"],
            "category": item["category"],
            "query": query,
            "dense": dense_metrics,
            "hybrid": hybrid_metrics,
        })

    metric_names = [
        "recall_at_5",
        "recall_at_10",
        "mrr",
        "ndcg_at_5",
        "ndcg_at_10",
        "retrieval_latency_ms",
    ]

    aggregate = {}
    comparisons = {}

    for metric in metric_names:
        dense_values = [q["dense"][metric] for q in per_query]
        hybrid_values = [q["hybrid"][metric] for q in per_query]

        aggregate[f"dense_{metric}"] = bootstrap_mean_ci(
            dense_values,
            iterations=args.bootstrap_iterations,
        )
        aggregate[f"hybrid_{metric}"] = bootstrap_mean_ci(
            hybrid_values,
            iterations=args.bootstrap_iterations,
        )
        comparisons[metric] = paired_bootstrap_delta_ci(
            dense_values,
            hybrid_values,
            iterations=args.bootstrap_iterations,
        )

    categories = {}
    for item in per_query:
        categories.setdefault(item["category"], []).append(item)

    category_summary = {}
    for category, rows in categories.items():
        category_summary[category] = {
            "queries": len(rows),
            "dense_ndcg_at_10": statistics.fmean(
                row["dense"]["ndcg_at_10"] for row in rows
            ),
            "hybrid_ndcg_at_10": statistics.fmean(
                row["hybrid"]["ndcg_at_10"] for row in rows
            ),
            "dense_recall_at_10": statistics.fmean(
                row["dense"]["recall_at_10"] for row in rows
            ),
            "hybrid_recall_at_10": statistics.fmean(
                row["hybrid"]["recall_at_10"] for row in rows
            ),
        }

    payload = {
        "experiment": "Dense vs Hybrid",
        "experiment_version": "v0.1",
        "benchmark_version": benchmark["benchmark_version"],
        "corpus": benchmark["corpus"],
        "configuration": benchmark.get("configuration", {}),
        "methodology": {
            "baseline": "Dense retrieval",
            "treatment": "Dense + BM25 + RRF",
            "same_corpus": True,
            "same_queries": True,
            "same_judgments": True,
            "reranker_included": False,
            "paired_comparison": True,
            "bootstrap_iterations": args.bootstrap_iterations,
        },
        "aggregate": aggregate,
        "paired_comparisons": comparisons,
        "category_summary": category_summary,
        "queries": per_query,
        "benchmark_file_sha256": sha256_file(benchmark_path),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps({
        "experiment": payload["experiment"],
        "queries": len(per_query),
        "output": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
