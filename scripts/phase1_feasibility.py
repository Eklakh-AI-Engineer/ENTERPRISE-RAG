#!/usr/bin/env python3
"""Measure Phase 1 inference/resource characteristics."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tree_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size

    ignored = {".git", ".venv", "venv", "node_modules", "__pycache__"}
    total = 0

    for child in path.rglob("*"):
        if any(part in ignored for part in child.parts):
            continue
        if child.is_file():
            total += child.stat().st_size

    return total


def peak_rss_mb() -> float | None:
    status = Path("/proc/self/status")
    if not status.exists():
        return None

    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmHWM:"):
            kb = float(line.split()[1])
            return round(kb / 1024, 2)

    return None


def distribution_size(name: str) -> int | None:
    try:
        distribution = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return None

    total = 0
    for relative in distribution.files or []:
        try:
            total += Path(distribution.locate_file(relative)).stat().st_size
        except OSError:
            continue
    return total


def model_benchmark(concurrency: int) -> dict:
    import_start = time.perf_counter()
    from sentence_transformers import CrossEncoder, SentenceTransformer
    library_import_ms = (time.perf_counter() - import_start) * 1000

    dense_name = os.getenv(
        "DENSE_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )
    reranker_name = os.getenv(
        "RERANKER_MODEL",
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
    )

    result = {
        "dense_model": dense_name,
        "reranker_model": reranker_name,
        "library_import_ms": round(library_import_ms, 2),
    }

    start = time.perf_counter()
    dense = SentenceTransformer(dense_name)
    result["dense_initialization_ms"] = round(
        (time.perf_counter() - start) * 1000, 2
    )

    start = time.perf_counter()
    reranker = CrossEncoder(reranker_name)
    result["reranker_initialization_ms"] = round(
        (time.perf_counter() - start) * 1000, 2
    )

    query = "How does the retrieval pipeline rank evidence?"
    documents = [
        "Dense retrieval finds semantically similar evidence.",
        "BM25 retrieves lexical matches using term statistics.",
        "A cross encoder reranks query-document pairs.",
        "The generator produces an evidence-grounded answer.",
    ]

    start = time.perf_counter()
    dense.encode([query], normalize_embeddings=True)
    result["dense_query_ms"] = round(
        (time.perf_counter() - start) * 1000, 2
    )

    pairs = [[query, document] for document in documents]
    start = time.perf_counter()
    reranker.predict(pairs)
    result["reranker_batch_ms"] = round(
        (time.perf_counter() - start) * 1000, 2
    )

    def one_request() -> float:
        started = time.perf_counter()
        dense.encode([query], normalize_embeddings=True)
        reranker.predict(pairs)
        return (time.perf_counter() - started) * 1000

    workers = max(1, concurrency)
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        durations = list(executor.map(lambda _: one_request(), range(workers)))

    result["concurrency"] = workers
    result["concurrent_wall_ms"] = round(
        (time.perf_counter() - start) * 1000, 2
    )
    result["concurrent_request_ms"] = [
        round(value, 2) for value in durations
    ]
    result["peak_rss_mb"] = peak_rss_mb()

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-models", action="store_true")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--output", default="phase1-feasibility.json")
    args = parser.parse_args()

    payload = {
        "python": sys.version,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "deployable_source_bytes": tree_size(ROOT),
        "peak_rss_mb_before_models": peak_rss_mb(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "packages": {
            name: distribution_size(name)
            for name in (
                "fastapi",
                "uvicorn",
                "numpy",
                "faiss-cpu",
                "sentence-transformers",
                "rank-bm25",
                "langchain-text-splitters",
                "PyMuPDF",
                "openai",
            )
        },
    }

    if args.load_models:
        payload["model_benchmark"] = model_benchmark(max(1, args.concurrency))
    else:
        payload["model_benchmark"] = {
            "status": "skipped",
            "reason": "Run with --load-models on the target runtime.",
        }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
