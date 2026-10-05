from difflib import SequenceMatcher
from pathlib import Path

import io

import pymupdf
import pytesseract
from PIL import Image


PARSER_VERSION = "pdf-parser-v2-ocr"
DEFAULT_OCR_MIN_TEXT_CHARS = 100
DEFAULT_OCR_DPI = 180


def should_use_ocr(native_text: str, ocr_text: str, *, min_text_chars: int) -> bool:
    """Allow OCR fallback only when it meaningfully improves extraction quality."""

    cleaned_native = clean_text(native_text)
    cleaned_ocr = clean_text(ocr_text)

    if not cleaned_ocr.strip():
        return False

    if len(cleaned_ocr) < min_text_chars:
        return False

    alphanumeric_ratio = sum(character.isalnum() for character in cleaned_ocr) / len(cleaned_ocr)
    words = cleaned_ocr.split()
    if alphanumeric_ratio < 0.5 or len(set(words)) < 3:
        return False

    if len(cleaned_ocr) <= len(cleaned_native):
        return False

    if cleaned_native and SequenceMatcher(None, cleaned_native, cleaned_ocr).ratio() >= 0.95:
        return False

    gain_ratio = (len(cleaned_ocr) - len(cleaned_native)) / max(1, len(cleaned_native))
    if len(cleaned_native) >= min_text_chars and gain_ratio < 0.25:
        return False

    return True


def clean_text(text: str) -> str:
    """Normalize extracted PDF text."""

    lines = []

    for line in text.splitlines():
        line = " ".join(line.split())

        if line:
            lines.append(line)

    return "\n".join(lines)


def _ocr_page(page, dpi: int) -> str:
    """OCR a scanned PDF page when native PDF text is unavailable."""

    scale = dpi / 72
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    return pytesseract.image_to_string(image, config="--psm 6")


def parse_pdf(
    pdf_path: str,
    *,
    ocr_enabled: bool = True,
    ocr_min_text_chars: int = DEFAULT_OCR_MIN_TEXT_CHARS,
    ocr_dpi: int = DEFAULT_OCR_DPI,
) -> list[dict]:
    """
    Extract page-level content from a PDF.

    Native PDF text extraction is preferred. Pages with insufficient native
    text fall back to Tesseract OCR so scanned policy PDFs remain searchable.

    Returns one dictionary per page with stable provenance metadata.
    """

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    document_id = path.stem
    doc = pymupdf.open(path)
    pages = []

    try:
        for page_number, page in enumerate(doc, start=1):
            native_text = clean_text(page.get_text("text"))
            text = native_text
            extraction_method = "native"
            extraction_status = "native_sufficient" if len(native_text) >= ocr_min_text_chars else "native_insufficient"
            extraction_error = None

            if ocr_enabled and len(native_text) < ocr_min_text_chars:
                try:
                    ocr_text = clean_text(_ocr_page(page, ocr_dpi))
                except Exception as error:
                    extraction_status = "ocr_failed"
                    extraction_error = f"{type(error).__name__}: {error}"
                else:
                    if should_use_ocr(native_text, ocr_text, min_text_chars=ocr_min_text_chars):
                        text = ocr_text
                        extraction_method = "ocr:tesseract"
                        extraction_status = "ocr_used"
                    else:
                        extraction_status = "ocr_rejected"

            page_result = {
                "document_id": document_id,
                "source": path.name,
                "page": page_number,
                "doc_type": "pdf",
                "text": text,
                "extraction_method": extraction_method,
                "extraction_status": extraction_status,
                "parser_version": PARSER_VERSION,
            }
            if extraction_error is not None:
                page_result["extraction_error"] = extraction_error
            pages.append(page_result)
    finally:
        doc.close()

    return pages
