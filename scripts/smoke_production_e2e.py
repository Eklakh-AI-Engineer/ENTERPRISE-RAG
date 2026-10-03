"""Authenticated production smoke test for the complete RAG upload path.

Required environment:
  E2E_API_BASE_URL
  E2E_SUPABASE_URL
  E2E_SUPABASE_PUBLISHABLE_KEY
  E2E_EMAIL
  E2E_PASSWORD
  E2E_PDF_PATH

Optional:
  E2E_TIMEOUT_SECONDS=180
  E2E_POLL_SECONDS=5

The script intentionally uses a real user session and the public/publishable
Supabase key. It never accepts or prints a service-role key.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests


def env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    api = env("E2E_API_BASE_URL").rstrip("/")
    supabase = env("E2E_SUPABASE_URL").rstrip("/")
    publishable_key = env("E2E_SUPABASE_PUBLISHABLE_KEY")
    email = env("E2E_EMAIL")
    password = env("E2E_PASSWORD")
    pdf_path = Path(env("E2E_PDF_PATH"))

    timeout = int(os.getenv("E2E_TIMEOUT_SECONDS", "180"))
    poll_seconds = float(os.getenv("E2E_POLL_SECONDS", "5"))

    if not pdf_path.is_file():
        raise SystemExit(f"PDF does not exist: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise SystemExit("E2E_PDF_PATH must point to a PDF file.")

    headers = {
        "apikey": publishable_key,
        "Content-Type": "application/json",
    }
    auth = requests.post(
        f"{supabase}/auth/v1/token?grant_type=password",
        headers=headers,
        json={"email": email, "password": password},
        timeout=30,
    )
    auth.raise_for_status()
    access_token = auth.json().get("access_token")
    if not access_token:
        raise RuntimeError("Supabase login returned no access token.")

    bearer = {"Authorization": f"Bearer {access_token}"}

    me = requests.get(f"{api}/auth/me", headers=bearer, timeout=30)
    me.raise_for_status()
    print(f"[1/4] authenticated user: {me.json()['user_id']}")

    with pdf_path.open("rb") as handle:
        upload = requests.post(
            f"{api}/documents",
            headers=bearer,
            files={"file": (pdf_path.name, handle, "application/pdf")},
            timeout=60,
        )
    upload.raise_for_status()
    document = upload.json()
    document_id = document["document_id"]
    print(f"[2/4] upload accepted: document={document_id}")

    deadline = time.monotonic() + timeout
    last_status = None
    while time.monotonic() < deadline:
        status = requests.get(
            f"{api}/documents/{document_id}",
            headers=bearer,
            timeout=30,
        )
        status.raise_for_status()
        payload = status.json()
        current = payload["status"]
        if current != last_status:
            print(f"[3/4] document status: {current}")
            last_status = current
        if current == "READY":
            break
        if current == "FAILED":
            raise RuntimeError("Production ingestion marked the document FAILED.")
        time.sleep(poll_seconds)
    else:
        raise TimeoutError(
            f"Document did not reach READY within {timeout} seconds."
        )

    query = requests.post(
        f"{api}/query",
        headers={**bearer, "Content-Type": "application/json"},
        json={"query": "Summarize the uploaded document."},
        timeout=120,
    )
    query.raise_for_status()
    result = query.json()
    if not result.get("answer"):
        raise RuntimeError("Query returned no answer.")
    print("[4/4] authenticated query returned an answer.")
    print("PRODUCTION E2E PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as exc:
        body = exc.response.text[:500] if exc.response is not None else ""
        print(f"PRODUCTION E2E FAIL: HTTP {exc.response.status_code}: {body}")
        raise SystemExit(1) from exc
