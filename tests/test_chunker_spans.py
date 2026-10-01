from app.chunking.recursive_chunker import RecursiveChunker


def test_chunks_have_durable_page_spans():
    page = {
        "document_id": "doc-1",
        "source": "sample.pdf",
        "page": 1,
        "doc_type": "pdf",
        "text": "Alpha sentence. Beta sentence. Gamma sentence.",
    }

    chunks = RecursiveChunker(
        chunk_size=20,
        chunk_overlap=5,
    ).chunk_pages([page])

    assert chunks
    for chunk in chunks:
        assert 0 <= chunk["start_char"] < chunk["end_char"] <= len(page["text"])
        assert page["text"][chunk["start_char"]:chunk["end_char"]] == chunk["text"]
        assert chunk["chunker_version"] == "recursive-v2-span"
