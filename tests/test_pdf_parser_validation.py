from app.chunking.recursive_chunker import RecursiveChunker
from app.parsing import pdf_parser


class _FakePage:
    def __init__(self, native_text: str):
        self.native_text = native_text

    def get_text(self, _mode):
        return self.native_text


class _FakeDoc:
    def __init__(self, pages):
        self.pages = pages
        self.closed = False

    def __iter__(self):
        return iter(self.pages)

    def close(self):
        self.closed = True


def _run_parse(monkeypatch, tmp_path, native_pages, ocr, *, threshold=100):
    pdf_path = tmp_path / "stable-document-id.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    document = _FakeDoc([_FakePage(text) for text in native_pages])
    monkeypatch.setattr(pdf_parser.pymupdf, "open", lambda _path: document)
    calls = []

    def fake_ocr(page, dpi):
        calls.append((page, dpi))
        if isinstance(ocr, Exception):
            raise ocr
        return ocr[len(calls) - 1] if isinstance(ocr, list) else ocr

    monkeypatch.setattr(pdf_parser, "_ocr_page", fake_ocr)
    pages = pdf_parser.parse_pdf(str(pdf_path), ocr_min_text_chars=threshold)
    return pages, calls, document


def test_sufficient_native_text_skips_ocr(monkeypatch, tmp_path):
    native = "Native policy content. " * 8
    pages, calls, _document = _run_parse(
        monkeypatch, tmp_path, [native], "OCR must not run", threshold=100
    )

    assert calls == []
    assert pages[0]["text"] == pdf_parser.clean_text(native)
    assert pages[0]["extraction_method"] == "native"
    assert pages[0]["extraction_status"] == "native_sufficient"


def test_insufficient_native_text_attempts_ocr(monkeypatch, tmp_path):
    pages, calls, _document = _run_parse(
        monkeypatch,
        tmp_path,
        ["Short native text."],
        "Recovered policy content. " * 8,
        threshold=100,
    )

    assert len(calls) == 1
    assert pages[0]["extraction_method"] == "ocr:tesseract"
    assert pages[0]["extraction_status"] == "ocr_used"


def test_meaningful_better_ocr_is_used_with_stable_page_identity(monkeypatch, tmp_path):
    ocr_text = "Recovered policy content with meaningful words. " * 5
    pages, _calls, _document = _run_parse(
        monkeypatch, tmp_path, ["Scan"], ocr_text, threshold=100
    )

    assert pages[0]["text"] == pdf_parser.clean_text(ocr_text)
    assert pages[0]["document_id"] == "stable-document-id"
    assert pages[0]["page"] == 1
    assert pages[0]["extraction_method"] == "ocr:tesseract"
    chunks = RecursiveChunker(chunk_size=80, chunk_overlap=10).chunk_pages(pages)
    assert chunks
    assert all(chunk["document_id"] == "stable-document-id" for chunk in chunks)
    assert all(chunk["page"] == 1 for chunk in chunks)
    assert all(pages[0]["text"][chunk["start_char"]:chunk["end_char"]] == chunk["text"] for chunk in chunks)


def test_empty_or_poor_ocr_does_not_replace_useful_native_text(monkeypatch, tmp_path):
    native = "Native text with useful policy detail."
    pages, calls, _document = _run_parse(
        monkeypatch, tmp_path, [native], "###", threshold=100
    )

    assert len(calls) == 1
    assert pages[0]["text"] == native
    assert pages[0]["extraction_method"] == "native"
    assert pages[0]["extraction_status"] == "ocr_rejected"


def test_ocr_failure_is_explicit_and_native_text_is_preserved(monkeypatch, tmp_path):
    native = "Native text with useful policy detail."
    pages, calls, document = _run_parse(
        monkeypatch,
        tmp_path,
        [native],
        RuntimeError("Tesseract is unavailable"),
        threshold=100,
    )

    assert len(calls) == 1
    assert pages[0]["text"] == native
    assert pages[0]["extraction_method"] == "native"
    assert pages[0]["extraction_status"] == "ocr_failed"
    assert pages[0]["extraction_error"] == "RuntimeError: Tesseract is unavailable"
    assert document.closed


def test_ocr_output_must_be_meaningful_not_just_long(monkeypatch, tmp_path):
    repeated_garbage = "!!!!!!!!!! " * 20
    pages, _calls, _document = _run_parse(
        monkeypatch, tmp_path, ["Useful native policy text."], repeated_garbage, threshold=100
    )

    assert pages[0]["text"] == "Useful native policy text."
    assert pages[0]["extraction_status"] == "ocr_rejected"