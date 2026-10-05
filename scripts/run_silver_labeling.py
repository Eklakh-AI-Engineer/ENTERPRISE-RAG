#!/usr/bin/env python3
"""
Phase 2 Silver Labeling — Resume-safe, rate-limit-resilient relevance judge.

Resumes from the existing checkpoint in cha_silver_labels_v1.json.
Processes all remaining queries (CHA-011 through CHA-050).

Usage:
    python scripts/run_silver_labeling.py

Environment variables required:
    OPENROUTER_API_KEY    — your OpenRouter API key
    SILVER_MODEL          — (optional) model override, defaults to nemotron free

Features:
    - Resumes from checkpoint without redoing completed queries
    - Exponential backoff on HTTP 429 (up to 5 retries, max 120s wait)
    - Batch size 4 candidates per API call
    - Validates model JSON output before accepting
    - Retries malformed responses up to 3 times
    - Checkpoints after every fully completed query
    - Preserves partial progress metadata on clean stop
    - Enforces judge-model provenance on every judgment
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────────

POOL_PATH = Path("data/evaluation/cha_pool_v1.json")
LABELS_PATH = Path("data/evaluation/cha_silver_labels_v1.json")

# Default model — override via SILVER_MODEL env var
# poolside/laguna-s-2.1:free  → 3.7s/batch, clean JSON, RECOMMENDED
# nvidia/nemotron-3.5-lightning:free → 126s/batch, thinking model, fallback
# qwen/qwen3.8-27b:free → fast but frequently rate-limited
DEFAULT_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    os.getenv(
        "SILVER_MODEL",
        "poolside/laguna-s-2.1:free",
    ),
)

BATCH_SIZE = 4           # candidates per API call
MAX_RETRIES_429 = 30      # further increased retries to survive extended rate limits
BASE_WAIT_429 = 15       # base wait seconds on first 429
MAX_WAIT_429 = 600       # extended cap on backoff (10 minutes)
MAX_RETRIES_MALFORMED = 3  # retries for bad JSON from model
API_TIMEOUT = 90           # seconds — free models can be slow
# 512 tokens is enough for direct-JSON models (Poolside).
# Set SILVER_MAX_TOKENS=2048 if using Nemotron (thinking model needs more room).
MAX_TOKENS = int(os.getenv("SILVER_MAX_TOKENS", "512"))
INTER_BATCH_SLEEP = 2.0  # seconds between successful batches
INTER_QUERY_SLEEP = 3.0  # seconds between completed queries

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("silver_labeler")

# ── Prompt ──────────────────────────────────────────────────────────────────

PROMPT_VERSION = "phase2-relevance-silver-v1"

SYSTEM_PROMPT = """You are a relevance judge for an enterprise document retrieval system.
Given a query and candidate text passages, rate each passage's relevance to the query.

Use this 4-point scale:
  0 = Not relevant (passage does not address the query at all)
  1 = Marginally relevant (mentions related topic but does not answer query)
  2 = Relevant (addresses the query but incompletely)
  3 = Highly relevant (directly and fully answers the query)

Respond ONLY with a JSON array. Each element must have:
  - "candidate_index": integer (0-based index within this batch)
  - "relevance": integer 0, 1, 2, or 3
  - "confidence": float between 0.0 and 1.0

Example output for a batch of 2:
[
  {"candidate_index": 0, "relevance": 3, "confidence": 0.95},
  {"candidate_index": 1, "relevance": 0, "confidence": 0.90}
]

Do not include any explanation, markdown, or extra text."""


def build_batch_prompt(query: str, candidates: list[dict], batch_offset: int) -> str:
    lines = [f'Query: "{query}"\n', "Candidates:"]
    for i, cand in enumerate(candidates):
        text = cand.get("text", "").strip()[:600]
        lines.append(f"\n[{i}] (pool index {batch_offset + i})\n{text}")
    lines.append("\nRate each candidate's relevance to the query. Return JSON array only.")
    return "\n".join(lines)


# ── OpenRouter API call ──────────────────────────────────────────────────────

def call_openrouter(api_key: str, model: str, prompt: str, *, temperature: float = 0.0) -> str:
    """Call OpenRouter with exponential backoff on 429. Returns raw text content."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/enterprise-rag",
        "X-Title": "Enterprise RAG Silver Labeler",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": MAX_TOKENS,
    }

    wait = BASE_WAIT_429
    for attempt in range(1, MAX_RETRIES_429 + 1):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=API_TIMEOUT)
        except requests.RequestException as exc:
            log.warning("Network error on attempt %d: %s", attempt, exc)
            if attempt == MAX_RETRIES_429:
                raise
            time.sleep(wait)
            wait = min(wait * 2, MAX_WAIT_429)
            continue

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", wait))
            actual_wait = max(retry_after, wait)
            log.warning(
                "HTTP 429 on attempt %d/%d — waiting %ds before retry...",
                attempt, MAX_RETRIES_429, actual_wait,
            )
            if attempt == MAX_RETRIES_429:
                raise RuntimeError(
                    f"OpenRouter HTTP 429 Too Many Requests — "
                    f"exhausted {MAX_RETRIES_429} retries. "
                    f"Run again later to resume from checkpoint."
                )
            time.sleep(actual_wait)
            wait = min(wait * 2, MAX_WAIT_429)
            continue

        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise ValueError("Model returned empty content")
        return content.strip()

    raise RuntimeError("Retry loop exhausted without returning")


# ── JSON parsing ─────────────────────────────────────────────────────────────

def extract_json_array(text: str) -> list[dict]:
    """Extract the JSON array from the model response.

    Thinking models (e.g. Nemotron) output a reasoning chain BEFORE the JSON.
    We find the LAST valid JSON array in the response to skip the reasoning.
    """
    # Strip markdown fences
    text = re.sub(r"```(?:json)?", "", text).strip()

    # Find ALL [...] blocks and try each from last to first
    matches = list(re.finditer(r"\[.*?\]", text, re.DOTALL))
    if not matches:
        # Fallback: try greedy match spanning the whole response
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON array found in response: {text[:300]!r}")
        matches = [match]

    for m in reversed(matches):  # try last match first (thinking model puts answer last)
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, list) and parsed:
                return parsed
        except json.JSONDecodeError:
            continue

    raise ValueError(f"No valid JSON array found in response: {text[:300]!r}")


def validate_batch_judgments(
    parsed: list[dict],
    batch_size: int,
    batch_offset: int,
    pool_size: int,
) -> list[dict]:
    """Validate and normalise judgments from one batch response."""
    if len(parsed) != batch_size:
        raise ValueError(f"Expected {batch_size} judgments, got {len(parsed)}")

    seen_pool_indices: set[int] = set()
    judgments = []
    for item in parsed:
        local_idx = int(item["candidate_index"])
        if local_idx < 0 or local_idx >= batch_size:
            raise ValueError(f"candidate_index {local_idx} out of range for batch size {batch_size}")
        pool_idx = batch_offset + local_idx
        if pool_idx >= pool_size:
            raise ValueError(f"Pool index {pool_idx} exceeds pool size {pool_size}")
        if pool_idx in seen_pool_indices:
            raise ValueError(f"Duplicate pool index {pool_idx}")
        seen_pool_indices.add(pool_idx)

        relevance = int(item["relevance"])
        if relevance not in (0, 1, 2, 3):
            raise ValueError(f"relevance {relevance} not in [0,1,2,3]")

        confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))

        judgments.append({
            "candidate_index": pool_idx,
            "relevance": relevance,
            "confidence": confidence,
        })

    return judgments


# ── Checkpoint I/O ────────────────────────────────────────────────────────────

def load_checkpoint() -> dict:
    if not LABELS_PATH.exists():
        raise FileNotFoundError(
            f"Checkpoint file not found: {LABELS_PATH}\n"
            "Expected the existing cha_silver_labels_v1.json checkpoint."
        )
    return json.loads(LABELS_PATH.read_text(encoding="utf-8"))


def save_checkpoint(state: dict) -> None:
    LABELS_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Checkpoint saved → %s", LABELS_PATH)


def build_completed_set(state: dict) -> set[str]:
    return {q["query_id"] for q in state.get("queries", [])}


# ── Core labeling loop ────────────────────────────────────────────────────────

def label_query(api_key: str, model: str, query_item: dict, state: dict) -> bool:
    """
    Label all candidates for a single query.
    Returns True if fully completed, False if stopped due to rate limiting.
    Appends the completed query to state["queries"] and saves checkpoint.
    """
    query_id = query_item["query_id"]
    query_text = query_item["query"]
    candidates = query_item["candidates"]
    pool_size = len(candidates)
    category = query_item.get("category", "")
    num_batches = -(-pool_size // BATCH_SIZE)  # ceil division

    log.info("Labeling %s — '%s' (%d candidates, %d batches)", query_id, query_text[:60], pool_size, num_batches)

    all_judgments: list[dict] = []

    for batch_num, batch_start in enumerate(range(0, pool_size, BATCH_SIZE), start=1):
        batch = candidates[batch_start: batch_start + BATCH_SIZE]
        prompt = build_batch_prompt(query_text, batch, batch_start)

        judgment_batch: list[dict] = []
        for malformed_attempt in range(1, MAX_RETRIES_MALFORMED + 1):
            try:
                raw = call_openrouter(api_key, model, prompt)
                parsed = extract_json_array(raw)
                judgment_batch = validate_batch_judgments(parsed, len(batch), batch_start, pool_size)
                break  # success

            except RuntimeError as exc:
                if "429" in str(exc):
                    log.error("Rate limit exhausted. Saving checkpoint and stopping.")
                    state.setdefault("partial_queries", {})[query_id] = {
                        "query_id": query_id,
                        "candidate_count": pool_size,
                        "judgments_so_far": len(all_judgments),
                    }
                    state["status"] = "rate_limited"
                    state["last_stop_reason"] = str(exc)
                    save_checkpoint(state)
                    return False
                raise

            except (ValueError, json.JSONDecodeError, KeyError) as exc:
                log.warning(
                    "Malformed response on attempt %d/%d for %s batch %d: %s",
                    malformed_attempt, MAX_RETRIES_MALFORMED, query_id, batch_num, exc,
                )
                if malformed_attempt == MAX_RETRIES_MALFORMED:
                    log.error("Skipping %s batch %d — using default label 0.", query_id, batch_num)
                    judgment_batch = [
                        {"candidate_index": batch_start + i, "relevance": 0, "confidence": 0.0}
                        for i in range(len(batch))
                    ]
                else:
                    time.sleep(2)
                    continue

        # Attach chunk_id and provenance
        for j in judgment_batch:
            j["chunk_id"] = candidates[j["candidate_index"]]["chunk_id"]
            j["label_source"] = "silver_ai"

        all_judgments.extend(judgment_batch)
        log.info("  %s batch %d/%d — %d judgments so far", query_id, batch_num, num_batches, len(all_judgments))
        time.sleep(INTER_BATCH_SLEEP)

    # Query complete
    state["queries"].append({
        "query_id": query_id,
        "category": category,
        "query": query_text,
        "candidate_count": pool_size,
        "judgments": sorted(all_judgments, key=lambda j: j["candidate_index"]),
    })
    state["completed_queries"] = len(state["queries"])
    state["completed_judgments"] = sum(len(q["judgments"]) for q in state["queries"])
    state["status"] = "in_progress"
    state.pop("last_stop_reason", None)
    state.get("partial_queries", {}).pop(query_id, None)

    save_checkpoint(state)
    log.info(
        "✓ %s complete — %d/%d queries, %d total judgments",
        query_id, state["completed_queries"], state["total_queries"], state["completed_judgments"],
    )
    time.sleep(INTER_QUERY_SLEEP)
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "OPENROUTER_API_KEY environment variable is not set.\n"
            "Set it in your .env file or export it in your shell."
        )

    model = DEFAULT_MODEL.strip()
    log.info("Judge model  : %s", model)
    log.info("Prompt ver   : %s", PROMPT_VERSION)
    log.info("Pool         : %s", POOL_PATH)
    log.info("Checkpoint   : %s", LABELS_PATH)

    pool_data = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    pool_queries: list[dict] = pool_data["queries"]
    log.info("Pool         : %d queries, %d total candidates",
             len(pool_queries),
             sum(q["candidate_count"] for q in pool_queries))

    state = load_checkpoint()
    state.setdefault("queries", [])
    state.setdefault("partial_queries", {})
    state.setdefault("total_queries", len(pool_queries))
    state["model"] = model
    state["prompt_version"] = PROMPT_VERSION

    completed = build_completed_set(state)
    remaining = [q for q in pool_queries if q["query_id"] not in completed]

    log.info(
        "Resume point : %d/%d queries complete — %d remaining",
        len(completed), len(pool_queries), len(remaining),
    )

    if not remaining:
        log.info("All queries already labeled. Marking complete.")
        state["status"] = "complete"
        save_checkpoint(state)
        return

    stopped_early = False
    for query_item in remaining:
        if not label_query(api_key, model, query_item, state):
            stopped_early = True
            break

    if stopped_early:
        total_candidates = sum(q["candidate_count"] for q in pool_queries)
        log.warning(
            "Stopped due to rate limiting — %d/%d queries, %d/%d judgments done. Re-run to resume.",
            state["completed_queries"], state["total_queries"],
            state["completed_judgments"], total_candidates,
        )
    else:
        state["status"] = "complete"
        state.pop("last_stop_reason", None)
        save_checkpoint(state)
        log.info(
            "ALL DONE — %d queries, %d judgments",
            state["completed_queries"], state["completed_judgments"],
        )


if __name__ == "__main__":
    main()
