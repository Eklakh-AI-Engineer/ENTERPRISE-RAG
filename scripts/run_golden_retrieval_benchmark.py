#!/usr/bin/env python3
"""Run the frozen Enterprise RAG retrieval benchmark.

The benchmark must contain 50-100 human-verified relevance judgments.
This runner intentionally refuses draft/unlabelled datasets so development
runs cannot be presented as benchmark results.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from app.evaluation.retrieval_metrics import (
    bootstrap_mean_ci,
    ndcg_at_k,
    paired_bootstrap_delta_ci,
)
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.hybrid.retriever import HybridRetriever
from app.reranking.cross_encoder import CrossEncoderReranker


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def unwrap_chunks(payload):
    if isinstance(payload, dict) and "chunks" in payload:
        return payload["chunks"]
    return payload


def matches(chunk: dict, judgment: dict) -> bool:
    if (judgment.get("document_id") or "") != (
        chunk.get("document_id") or chunk.get("document") or chunk.get("source")
    ):
        return False
    if judgment.get("page") != chunk.get("page"):
        return False

    start_a, end_a = chunk.get("start_char"), chunk.get("end_char")
    start_b, end_b = judgment.get("start_char"), judgment.get("end_char")

    if all(isinstance(v, int) for v in (start_a, end_a, start_b, end_b)):
        return max(start_a, start_b) < min(end_a, end_b)

    return judgment.get("chunk_id") == chunk.get("chunk_id")


def relevance_map(chunks, judgments):
    result = {}
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        if not chunk_id:
            continue
        result[chunk_id] = max(
            (float(j["relevance"]) for j in judgments if matches(chunk, j)),
            default=0.0,
        )
    return result


def evaluate_ranked(results, chunks, judgments, top_k):
    ranked = [r for r in results if r.get("chunk_id")]
    ids = [r["chunk_id"] for r in ranked]
    rel = relevance_map(chunks, judgments)
    positive = {k for k, v in rel.items() if v > 0}

    def recall(k):
        if not positive:
            return 0.0
        return len(set(ids[:k]) & positive) / len(positive)

    first = next(
        (1.0 / rank for rank, chunk_id in enumerate(ids, 1) if rel.get(chunk_id, 0) > 0),
        0.0,
    )

    return {
        "recall_at_5": recall(5),
        "recall_at_10": recall(10),
        "mrr": first,
        "ndcg_at_5": ndcg_at_k(ids, rel, 5),
        "ndcg_at_10": ndcg_at_k(ids, rel, 10),
        "candidate_count": len(ranked),
    }


def validate_benchmark(benchmark):
    if benchmark.get("status") != "frozen":
        raise SystemExit(
            "Benchmark is not frozen. Complete human annotation first and set status to 'frozen'."
        )

    queries = benchmark.get("queries", [])
    if not 50 <= len(queries) <= 100:
        raise SystemExit(f"Expected 50-100 queries; found {len(queries)}.")

    for item in queries:
        if not item.get("query") or not item.get("query_id"):
            raise SystemExit("Every query requires query_id and query.")
        if not item.get("relevance"):
            raise SystemExit(f"{item['query_id']} has no human relevance judgments.")
        for j in item["relevance"]:
            for key in ("document_id", "page", "start_char", "end_char", "relevance"):
                if key not in j:
                    raise SystemExit(f"{item['query_id']} missing relevance field: {key}")
            if not 0 <= int(j["relevance"]) <= 3:
                raise SystemExit(f"{item['query_id']} has relevance outside 0-3.")


def run(args):
    benchmark = load_json(args.benchmark)
    validate_benchmark(benchmark)
    chunks = unwrap_chunks(load_json(args.chunks))

    dense = DenseRetriever()
    dense.build_index(chunks)

    bm25 = BM25Retriever()
    bm25.build_index(chunks)

    hybrid = HybridRetriever(dense_retriever=dense, bm25_retriever=bm25)
    reranker = CrossEncoderReranker() if "reranker" in args.systems else None

    per_query = []

    for item in benchmark["queries"]:
        row = {
            "query_id": item["query_id"],
            "category": item["category"],
            "query": item["query"],
            "systems": {},
        }

        for system in args.systems:
            start = time.perf_counter()

            if system == "dense":
                results = dense.search(item["query"], top_k=args.top_k)
            elif system == "bm25":
                results = bm25.search(item["query"], top_k=args.top_k)
            elif system == "hybrid":
                results = hybrid.search(
                    item["query"],
                    top_k=args.top_k,
                    candidate_k=args.candidate_k,
                )
            elif system == "reranker":
                candidates = hybrid.search(
                    item["query"],
                    top_k=args.candidate_k,
                    candidate_k=args.candidate_k,
                )
                results = reranker.rerank(
                    item["query"], candidates, top_k=args.top_k
                )
            else:
                raise SystemExit(f"Unsupported system: {system}")

            latency_ms = (time.perf_counter() - start) * 1000
            metrics = evaluate_ranked(
                results, chunks, item["relevance"], args.top_k
            )
            metrics["retrieval_latency_ms"] = round(latency_ms, 2)
            row["systems"][system] = metrics

        per_query.append(row)

    aggregate = {}
    for system in args.systems:
        for metric in (
            "recall_at_5",
            "recall_at_10",
            "mrr",
            "ndcg_at_5",
            "ndcg_at_10",
            "retrieval_latency_ms",
        ):
            values = [q["systems"][system][metric] for q in per_query]
            aggregate[f"{system}_{metric}"] = bootstrap_mean_ci(
                values, iterations=args.bootstrap_iterations
            )

    paired = {}
    if "dense" in args.systems and "hybrid" in args.systems:
        for metric in ("recall_at_5", "recall_at_10", "mrr", "ndcg_at_5", "ndcg_at_10"):
            baseline = [q["systems"]["dense"][metric] for q in per_query]
            treatment = [q["systems"]["hybrid"][metric] for q in per_query]
            paired[f"hybrid_minus_dense_{metric}"] = paired_bootstrap_delta_ci(
                baseline,
                treatment,
                iterations=args.bootstrap_iterations,
            )

    categories = {}
    for q in per_query:
        categories.setdefault(q["category"], []).append(q)

    category_summary = {}
    for category, rows in categories.items():
        category_summary[category] = {
            "queries": len(rows),
            "systems": {
                system: {
                    metric: statistics.fmean(
                        r["systems"][system][metric] for r in rows
                    )
                    for metric in ("recall_at_5", "mrr", "ndcg_at_10")
                }
                for system in args.systems
            },
        }

    payload = {
        "benchmark_version": benchmark["benchmark_version"],
        "corpus_id": benchmark["corpus_id"],
        "configuration": {
            "systems": args.systems,
            "top_k": args.top_k,
            "candidate_k": args.candidate_k,
            "bootstrap_iterations": args.bootstrap_iterations,
            "seed": 42,
        },
        "queries": per_query,
        "aggregate": aggregate,
        "paired_comparisons": paired,
        "category_summary": category_summary,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "queries": len(per_query),
        "systems": args.systems,
        "output": str(output),
    }, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark",
        default="data/evaluation/golden_queries_v1.json",
    )
    parser.add_argument(
        "--chunks",
        default="data/processed/cha_chunks.json",
    )
    parser.add_argument(
        "--systems",
        nargs="+",
        choices=("dense", "bm25", "hybrid", "reranker"),
        default=("dense", "bm25", "hybrid", "reranker"),
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--bootstrap-iterations", type=int, default=10000)
    parser.add_argument(
        "--output",
        default="data/evaluation/results/golden_v1.json",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
