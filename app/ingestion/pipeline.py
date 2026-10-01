from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.chunking.recursive_chunker import RecursiveChunker
from app.parsing.pdf_parser import parse_pdf


@dataclass(frozen=True, slots=True)
class IngestionArtifact:
    pages: list[dict]
    chunks: list[dict]
    parser_version: str
    chunker_version: str


class PdfIngestionPipeline:
    """Pure pipeline boundary: bytes -> page evidence -> durable chunks.

    Embedding, database writes, and indexing are deliberately outside this
    component. That keeps parsing/chunking deterministic and independently testable.
    """

    def __init__(
        self,
        *,
        parser: Callable[..., list[dict]] = parse_pdf,
        chunker: RecursiveChunker | None = None,
    ) -> None:
        self.parser = parser
        self.chunker = chunker or RecursiveChunker()

    def run(self, *, content: bytes, filename: str, document_id: str) -> IngestionArtifact:
        if not content:
            raise ValueError("document content must not be empty")
        if not filename.lower().endswith(".pdf"):
            raise ValueError("ingestion pipeline currently accepts PDF documents only")

        with tempfile.TemporaryDirectory(prefix="enterprise-rag-ingest-") as tmp:
            path = Path(tmp) / filename
            path.write_bytes(content)
            pages = self.parser(str(path))

        # Replace parser-local stem identity with the persisted document ID so
        # chunk identity never depends on the uploaded filename.
        normalized_pages = []
        for page in pages:
            normalized = dict(page)
            normalized["document_id"] = document_id
            normalized_pages.append(normalized)

        chunks = self.chunker.chunk_pages(normalized_pages)
        parser_version = pages[0].get("parser_version", "unknown") if pages else "unknown"
        return IngestionArtifact(
            pages=normalized_pages,
            chunks=chunks,
            parser_version=parser_version,
            chunker_version=self.chunker.VERSION,
        )
