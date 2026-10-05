from copy import deepcopy

import pytest

from app.chunking.recursive_chunker import (
    RecursiveChunker,
    validate_stable_evidence_metadata,
)
from app.citations.mapper import map_citations


def make_page():
    return {
        "document_id": "doc-1",
        "source": "policy.pdf",
        "page": 2,
        "section": "Leave Policy",
        "doc_type": "pdf",
        "text": "Alpha evidence. Beta evidence.",
    }


def test_valid_evidence_metadata_preserves_section_and_has_stable_identity():
    page = make_page()
    chunker = RecursiveChunker(chunk_size=18, chunk_overlap=3)

    first = chunker.chunk_pages([page])
    second = chunker.chunk_pages([page])

    assert first == second
    assert first
    assert all(chunk["document_id"] == "doc-1" for chunk in first)
    assert all(chunk["page"] == 2 for chunk in first)
    assert all(chunk["section"] == "Leave Policy" for chunk in first)
    assert all(chunk["chunk_id"] == f"doc-1-p002-c{chunk['chunk_index']:03d}" for chunk in first)
    validate_stable_evidence_metadata(
        first,
        {"doc-1": {2: page["text"]}},
        {"doc-1": {2: page["section"]}},
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda chunk: chunk.pop("document_id"), "missing required fields"),
        (lambda chunk: chunk.pop("section"), "missing required fields"),
        (lambda chunk: chunk.update(chunk_id=""), "chunk_id must be a non-empty string"),
        (lambda chunk: chunk.update(page=0), "page must be a positive integer"),
        (lambda chunk: chunk.update(start_char=-1), "chunk span is invalid"),
        (lambda chunk: chunk.update(end_char=0), "chunk span is invalid"),
        (lambda chunk: chunk.update(end_char=1000), "bounds exceed source page text"),
        (lambda chunk: chunk.update(chunk_id="other-p002-c001"), "chunk_id does not match metadata"),
        (
            lambda chunk: chunk.update(document_id="other", chunk_id="other-p002-c001"),
            "document/page is not present",
        ),
        (lambda chunk: chunk.update(text="corrupt"), "chunk text does not match page slice"),
        (lambda chunk: chunk.update(section="Other"), "chunk section does not match source page"),
    ],
)
def test_corrupted_evidence_metadata_fails_deterministically(mutation, message):
    page = make_page()
    chunk = RecursiveChunker(chunk_size=18, chunk_overlap=3).chunk_pages([page])[0]
    mutation(chunk)

    with pytest.raises(ValueError, match=message):
        validate_stable_evidence_metadata(
            [chunk],
            {"doc-1": {2: page["text"]}},
            {"doc-1": {2: page["section"]}},
        )


def test_duplicate_chunk_ids_are_rejected():
    page = make_page()
    chunks = RecursiveChunker(chunk_size=18, chunk_overlap=3).chunk_pages([page])
    chunks.append(deepcopy(chunks[0]))

    with pytest.raises(ValueError, match="duplicate chunk_id"):
        validate_stable_evidence_metadata(
            chunks,
            {"doc-1": {2: page["text"]}},
            {"doc-1": {2: page["section"]}},
        )


def test_citation_references_resolve_to_real_evidence_chunks():
    chunks = RecursiveChunker(chunk_size=100).chunk_pages([make_page()])
    answer = "The policy says this. [Source 1]"

    citations = map_citations(answer, chunks)

    assert citations[0]["chunk_id"] == chunks[0]["chunk_id"]
    assert citations[0]["document_id"] == chunks[0]["document_id"]


def test_citation_reference_without_chunk_identity_fails():
    with pytest.raises(ValueError, match="citation source does not resolve to a chunk"):
        map_citations("Evidence. [Source 1]", [{"document_id": "doc-1", "page": 2}])


def test_out_of_range_citation_reference_fails_instead_of_disappearing():
    chunks = RecursiveChunker(chunk_size=100).chunk_pages([make_page()])

    with pytest.raises(ValueError, match="citation source index does not resolve"):
        map_citations("Evidence. [Source 2]", chunks)