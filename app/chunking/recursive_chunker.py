from langchain_text_splitters import RecursiveCharacterTextSplitter


def validate_stable_evidence_metadata(
    chunks: list[dict],
    page_texts: dict[str, dict[int, str]] | None = None,
    page_sections: dict[str, dict[int, str | None]] | None = None,
) -> None:
    """Validate that each chunk keeps a stable, traceable page span."""

    seen_chunk_ids: set[str] = set()
    validate_page_spans = page_texts is not None

    if page_texts is None:
        page_texts = {}

    for chunk in chunks:
        missing_keys = {
            key for key in (
                "chunk_id",
                "document_id",
                "source",
                "page",
                "section",
                "chunk_index",
                "start_char",
                "end_char",
                "text",
            )
            if key not in chunk
        }
        if missing_keys:
            raise ValueError(f"chunk metadata missing required fields: {sorted(missing_keys)}")

        chunk_id = chunk["chunk_id"]
        document_id = chunk["document_id"]
        page = chunk["page"]
        chunk_index = chunk["chunk_index"]

        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id must be a non-empty string")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError("chunk_id must be a non-empty string")
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError(f"page must be a positive integer for {chunk_id}")
        if isinstance(chunk_index, bool) or not isinstance(chunk_index, int) or chunk_index < 1:
            raise ValueError(f"chunk_index must be a positive integer for {chunk_id}")

        if chunk_id in seen_chunk_ids:
            raise ValueError(f"duplicate chunk_id detected: {chunk_id}")
        seen_chunk_ids.add(chunk_id)

        expected_chunk_id = f"{document_id}-p{page:03d}-c{chunk_index:03d}"
        if chunk_id != expected_chunk_id:
            raise ValueError(
                f"chunk_id does not match metadata for {chunk_id}; expected {expected_chunk_id}"
            )

        start_char = chunk["start_char"]
        end_char = chunk["end_char"]
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (start_char, end_char)):
            raise ValueError(f"chunk offsets must be integers for {chunk_id}")
        if start_char < 0 or end_char <= start_char:
            raise ValueError(f"chunk span is invalid for {chunk_id}: [{start_char}, {end_char})")

        if validate_page_spans:
            document_pages = page_texts.get(document_id)
            if document_pages is None or page not in document_pages:
                raise ValueError(f"document/page is not present for {chunk_id}")
            page_text = document_pages[page]
            if end_char > len(page_text):
                raise ValueError(f"chunk bounds exceed source page text for {chunk_id}")
            slice_text = page_text[start_char:end_char]
            if slice_text != chunk["text"]:
                raise ValueError(
                    f"chunk text does not match page slice for {chunk_id}; "
                    f"expected {slice_text!r} but found {chunk['text']!r}"
                )

        if page_sections is not None:
            document_sections = page_sections.get(document_id)
            if document_sections is None or page not in document_sections:
                raise ValueError(f"source page section is not present for {chunk_id}")
            if chunk["section"] != document_sections[page]:
                raise ValueError(f"chunk section does not match source page for {chunk_id}")

    return None


class RecursiveChunker:

    VERSION = "recursive-v2-span"

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
        )

    def chunk_pages(self, pages: list[dict]) -> list[dict]:
        chunks = []
        page_text_map: dict[str, dict[int, str]] = {}
        page_section_map: dict[str, dict[int, str | None]] = {}

        for page in pages:
            document_id = page["document_id"]
            page_number = int(page["page"])
            page_text_map.setdefault(document_id, {})[page_number] = page["text"]
            page_section_map.setdefault(document_id, {})[page_number] = page.get("section")

        for page in pages:

            page_text = page["text"]

            if not page_text.strip():
                continue

            page_chunks = self.splitter.split_text(page_text)
            search_from = 0

            for index, text in enumerate(
                page_chunks,
                start=1,
            ):
                # Record character offsets so evaluation labels survive
                # chunker changes. The backward search window accounts for
                # the configured overlap between adjacent chunks.
                start_char = page_text.find(
                    text,
                    max(0, search_from - self.chunk_overlap),
                )

                if start_char < 0:
                    raise ValueError(
                        "Chunk text could not be mapped back to page offsets."
                    )

                end_char = start_char + len(text)
                search_from = end_char

                chunk_id = (
                    f"{page['document_id']}"
                    f"-p{page['page']:03d}"
                    f"-c{index:03d}"
                )

                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": page["document_id"],
                        "source": page["source"],
                        "page": page["page"],
                        "section": page.get("section"),
                        "doc_type": page["doc_type"],
                        "chunk_index": index,
                        "start_char": start_char,
                        "end_char": end_char,
                        "chunker_version": self.VERSION,
                        "text": text,
                    }
                )

        validate_stable_evidence_metadata(chunks, page_text_map, page_section_map)

        return chunks
