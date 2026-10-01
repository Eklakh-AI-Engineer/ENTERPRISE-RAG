# CHA Corpus v1 — Phase 2

The Phase 2 retrieval benchmark now uses four supplied Chicago Housing Authority policy PDFs.

## Documents

1. CHA Employee Handbook 2025 — 35 pages; native PDF text.
2. CHA Business Expense Reimbursement & Travel Policy — 6 pages; scanned PDF, OCR required.
3. CHA Information Security Policy — 8 pages; scanned PDF, OCR required.
4. CHA Procurement Policy — 5 pages; scanned PDF, OCR required.

The immutable SHA-256 hashes and source URLs are recorded in `cha_corpus_manifest.json`.

## Query set

`cha_queries_v1.json` contains 50 candidate evaluation queries across 10 categories, with exactly 5 queries per category.

This is **not yet the Phase 2 benchmark**. It intentionally contains no relevance judgments.

## Annotation protocol

1. Put the four PDFs in the local corpus input directory.
2. Parse with the repository PDF parser. Scanned pages use the Tesseract fallback.
3. Chunk with the current span-aware chunker.
4. Build Dense and BM25 retrieval indexes.
5. Build the unbiased Dense ∪ BM25 candidate pool.
6. Human-label every pooled candidate with relevance 0–3.
7. Freeze the benchmark with document/page/start_char/end_char evidence spans.
8. Run the controlled Dense-vs-Hybrid experiment.

Do not infer or manufacture relevance labels merely to reach the 50-query target.

## OCR note

Three of the four supplied PDFs are image-only. The parser therefore uses native extraction when sufficient text is present and falls back to Tesseract OCR when a page contains fewer than 100 native characters.
