from pathlib import Path

import pymupdf


def clean_text(text: str) -> str:
    """Normalize extracted PDF text."""

    lines = []

    for line in text.splitlines():
        line = " ".join(line.split())

        if line:
            lines.append(line)

    return "\n".join(lines)


def parse_pdf(pdf_path: str) -> list[dict]:
    """
    Extract page-level content from a PDF.

    Returns one dictionary per page with stable metadata.
    """

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    document_id = path.stem

    doc = pymupdf.open(path)

    pages = []

    for page_number, page in enumerate(doc, start=1):

        raw_text = page.get_text("text")
        text = clean_text(raw_text)

        page_record = {
            "document_id": document_id,
            "source": path.name,
            "page": page_number,
            "doc_type": "pdf",
            "text": text,
        }

        pages.append(page_record)

    doc.close()

    return pages