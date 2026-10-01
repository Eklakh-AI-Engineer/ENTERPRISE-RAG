from pathlib import Path

import io

import pymupdf
import pytesseract
from PIL import Image


PARSER_VERSION = "pdf-parser-v2-ocr"
DEFAULT_OCR_MIN_TEXT_CHARS = 100
DEFAULT_OCR_DPI = 180


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

    for page_number, page in enumerate(doc, start=1):
        native_text = clean_text(page.get_text("text"))
        text = native_text
        extraction_method = "native"

        if ocr_enabled and len(native_text) < ocr_min_text_chars:
            ocr_text = clean_text(_ocr_page(page, ocr_dpi))
            if len(ocr_text) > len(native_text):
                text = ocr_text
                extraction_method = "ocr:tesseract"

        pages.append(
            {
                "document_id": document_id,
                "source": path.name,
                "page": page_number,
                "doc_type": "pdf",
                "text": text,
                "extraction_method": extraction_method,
                "parser_version": PARSER_VERSION,
            }
        )

    doc.close()
    return pages
