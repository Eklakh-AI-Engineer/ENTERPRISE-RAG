from langchain_text_splitters import RecursiveCharacterTextSplitter


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
                        "section": None,
                        "doc_type": page["doc_type"],
                        "chunk_index": index,
                        "start_char": start_char,
                        "end_char": end_char,
                        "chunker_version": self.VERSION,
                        "text": text,
                    }
                )

        return chunks
