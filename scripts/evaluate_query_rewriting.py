#!/usr/bin/env python3
"""Paired frozen-golden comparison of original and rewritten queries."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

from app.config.settings import settings
from app.query.rewrite import QueryRewriter
from app.reranking.cross_encoder import CrossEncoderReranker
from app.retrieval.bm25.retriever import BM25Retriever
from app.retrieval.dense.retriever import DenseRetriever
from app.retrieval.hybrid.retriever import HybridRetriever
from scripts.run_golden_retrieval_benchmark import (
    evaluate_ranked,
    load_json,
    materialize_compact_human_labels,
    unwrap_chunks,
    validate_benchmark,
)

METRICS = ("recall_at_5", "recall_at_10", "mrr", "ndcg_at_5", "ndcg_at_10")
CATEGORY_METRICS = ("recall_at_5", "recall_at_10", "mrr", "ndcg_at_10")


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _retrieve(query, hybrid, reranker, *, top_k: int, candidate_k: int):
    candidates = hybrid.search(query, top_k=candidate_k, candidate_k=candidate_k)
    return reranker.rerank(query, candidates, top_k=top_k)


def _serialize_results(results: list[dict]) -> list[dict]:
    fields = (
        "chunk_id",
        "document_id",
        "source",
        "document",
        "page",
        "section",
        "start_char",
        "end_char",
        "text",
        "rrf_score",
        "rerank_score",
    )
    return [
        {"rank": rank, **{key: result.get(key) for key in fields if key in result}}
        for rank, result in enumerate(results, start=1)
    ]


def _aggregate(rows: list[dict], field: str) -> dict:
    baseline = statistics.fmean(row["baseline"][field] for row in rows)
    rewritten = statistics.fmean(row["rewritten"][field] for row in rows)
    delta = rewritten - baseline
    relative = (delta / baseline * 100.0) if baseline else (0.0 if not rewritten else None)
    return {
        "baseline": baseline,
        "rewritten": rewritten,
        "absolute_delta": delta,
        "relative_percent_delta": relative,
    }


def _classify(delta: float, tolerance: float = 1e-12) -> str:
    if delta > tolerance:
        return "improved"
    if delta < -tolerance:
        return "degraded"
    return "unchanged"


def run(args) -> dict:
    benchmark = load_json(args.benchmark)
    chunks = unwrap_chunks(load_json(args.chunks))
    human_review = benchmark.get("human_review", {})
    if human_review.get("labels_artifact"):
        benchmark = materialize_compact_human_labels(
            benchmark, human_review["labels_artifact"], args.pool
        )
    validate_benchmark(benchmark)

    dense = DenseRetriever(model_name=args.dense_model)
    dense.build_index(chunks)
    bm25 = BM25Retriever()
    bm25.build_index(chunks)
    hybrid = HybridRetriever(dense_retriever=dense, bm25_retriever=bm25)
    reranker = CrossEncoderReranker(model_name=args.reranker_model)
    rewriter = QueryRewriter(enabled=True)

    per_query = []
    for item in benchmark["queries"]:
        query = item["query"]
        rewritten_query = rewriter.rewrite(query)
        row = {
            "query_id": item["query_id"],
            "category": item["category"],
            "original_query": query,
            "rewritten_query": rewritten_query,
        }
        for condition, condition_query in (("baseline", query), ("rewritten", rewritten_query)):
            start = time.perf_counter()
            results = _retrieve(
                condition_query,
                hybrid,
                reranker,
                top_k=args.top_k,
                candidate_k=args.candidate_k,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            metrics = evaluate_ranked(results, chunks, item["relevance"], args.top_k)
            metrics["retrieval_latency_ms"] = latency_ms
            row[condition] = {
                "metrics": metrics,
                "retrieval_results": _serialize_results(results),
            }
        row["metric_deltas"] = {
            metric: row["rewritten"]["metrics"][metric] - row["baseline"]["metrics"][metric]
            for metric in METRICS
        }
        row["classification"] = _classify(row["metric_deltas"]["ndcg_at_10"])
        per_query.append(row)

    aggregate = {
        metric: _aggregate(
            [
                {"baseline": row["baseline"]["metrics"], "rewritten": row["rewritten"]["metrics"]}
                for row in per_query
            ],
            metric,
        )
        for metric in (*METRICS, "retrieval_latency_ms")
    }

    grouped = {}
    for row in per_query:
        grouped.setdefault(row["category"], []).append(row)
    category_analysis = {}
    for category, rows in sorted(grouped.items()):
        metric_comparison = {
            metric: _aggregate(
                [
                    {"baseline": row["baseline"]["metrics"], "rewritten": row["rewritten"]["metrics"]}
                    for row in rows
                ],
                metric,
            )
            for metric in CATEGORY_METRICS
        }
        category_analysis[category] = {
            "query_count": len(rows),
            "metrics": metric_comparison,
            "classification": _classify(metric_comparison["ndcg_at_10"]["absolute_delta"]),
        }

    query_level = {
        classification: [
            {
                "query_id": row["query_id"],
                "original_query": row["original_query"],
                "rewritten_query": row["rewritten_query"],
                "metric_deltas": row["metric_deltas"],
            }
            for row in per_query
            if row["classification"] == classification
        ]
        for classification in ("improved", "unchanged", "degraded")
    }

    labels = load_json(args.labels)
    payload = {
        "benchmark_version": benchmark["benchmark_version"],
        "corpus_id": benchmark["corpus_id"],
        "configuration": {
            "system": "hybrid_rrf_then_cross_encoder",
            "top_k": args.top_k,
            "candidate_k": args.candidate_k,
            "dense_model": args.dense_model,
            "reranker_model": args.reranker_model,
            "rewrite": {
                "enabled": True,
                "strategy": rewriter.STRATEGY,
                "feature_flag_default": False,
            },
            "judgment_count": labels["judgment_count"],
            "candidate_order_sha256": labels["candidate_order_sha256"],
            "scores_sha256": labels["scores_sha256"],
            "benchmark_sha256": _sha256(args.benchmark),
            "labels_sha256": _sha256(args.labels),
            "chunks_path": args.chunks,
        },
        "query_count": len(per_query),
        "aggregate": aggregate,
        "category_analysis": category_analysis,
        "query_level_analysis": {
            "classification_metric": "ndcg_at_10",
            **query_level,
        },
        "queries": per_query,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "query_count": len(per_query),
        "judgment_count": labels["judgment_count"],
        "system": payload["configuration"]["system"],
        "top_k": args.top_k,
        "candidate_k": args.candidate_k,
        "output": str(output),
    }, indent=2))
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="data/evaluation/golden_queries_v1.json")
    parser.add_argument("--labels", default="data/evaluation/human_labels_v1.json")
    parser.add_argument("--pool", default="data/evaluation/cha_pool_v1.json")
    parser.add_argument("--chunks", default="data/processed/cha_chunks.json")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--dense-model", default=settings.DENSE_MODEL)
    parser.add_argument("--reranker-model", default=settings.RERANKER_MODEL)
    parser.add_argument(
        "--output",
        default="data/evaluation/results/golden_v1_query_rewriting.json",
    )
    run(parser.parse_args())


if __name__ == "__main__":
    main()