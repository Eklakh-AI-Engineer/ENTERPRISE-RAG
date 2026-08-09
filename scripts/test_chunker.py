import json

from app.parsing.pdf_parser import parse_pdf
from app.chunking.recursive_chunker import RecursiveChunker


def main():
    pages = parse_pdf("data/raw/sample.pdf")

    chunker = RecursiveChunker(
        chunk_size=800,
        chunk_overlap=120,
    )

    chunks = chunker.chunk_pages(pages)

    print(f"\nPages: {len(pages)}")
    print(f"Chunks: {len(chunks)}")

    for chunk in chunks[:5]:
        print("\n" + "=" * 80)
        print(f"Chunk ID : {chunk['chunk_id']}")
        print(f"Document : {chunk['document_id']}")
        print(f"Source   : {chunk['source']}")
        print(f"Page     : {chunk['page']}")
        print(f"Index    : {chunk['chunk_index']}")
        print("=" * 80)
        print(chunk["text"])

    with open(
        "data/processed/sample_chunks.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\nSaved:")
    print("data/processed/sample_chunks.json")


if __name__ == "__main__":
    main()