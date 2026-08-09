from langchain_text_splitters import RecursiveCharacterTextSplitter


class RecursiveChunker:

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ):
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

            if not page["text"].strip():
                continue

            page_chunks = self.splitter.split_text(
                page["text"]
            )

            for index, text in enumerate(
                page_chunks,
                start=1,
            ):

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
                        "text": text,
                    }
                )

        return chunks