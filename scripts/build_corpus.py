#!/usr/bin/env python3
"""Build a span-aware chunk corpus from a directory of PDFs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.chunking.recursive_chunker import RecursiveChunker
from app.parsing.pdf_parser import parse_pdf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument(
        "--output",
        default="data/processed/cha_chunks.json",
    )
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=100)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    pdfs = sorted(input_dir.glob("*.pdf"))

    if not pdfs:
        raise SystemExit(f"No PDFs found in {input_dir}")

    pages = []
    extraction_counts = {"native": 0, "ocr:tesseract": 0}

    for pdf_path in pdfs:
        parsed = parse_pdf(str(pdf_path))
        pages.extend(parsed)
        for page in parsed:
            extraction_counts[page["extraction_method"]] = (
                extraction_counts.get(page["extraction_method"], 0) + 1
            )

    chunker = RecursiveChunker(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    chunks = chunker.chunk_pages(pages)

    payload = {
        "corpus_version": "cha-v1",
        "chunker_version": chunker.VERSION,
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "documents": [pdf.name for pdf in pdfs],
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "extraction_counts": extraction_counts,
        "chunks": chunks,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "documents": len(pdfs),
                "pages": len(pages),
                "chunks": len(chunks),
                "extraction_counts": extraction_counts,
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
