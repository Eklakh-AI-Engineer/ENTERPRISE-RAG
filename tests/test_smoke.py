from app.citations.verifier import CitationVerifier
from app.evaluation.retrieval_metrics import (
    hit_at_k,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.query.context import build_context


def test_retrieval_metrics():
    retrieved = ["a", "b", "c"]
    expected = ["c", "d"]

    assert recall_at_k(retrieved, expected) == 0.5
    assert precision_at_k(retrieved, expected) == 1 / 3
    assert hit_at_k(retrieved, expected) == 1.0
    assert reciprocal_rank(retrieved, expected) == 1 / 3
    assert mean_reciprocal_rank([retrieved], [expected]) == 1 / 3


def test_context_preserves_evidence_metadata():
    results = [
        {
            "chunk_id": "doc-p001-c001",
            "document_id": "doc",
            "document": "sample.pdf",
            "page": 1,
            "section": "Intro",
            "text": "Evidence text.",
        }
    ]

    context = build_context(results)

    assert "[SOURCE 1]" in context
    assert "Document: sample.pdf" in context
    assert "Page: 1" in context
    assert "Chunk ID: doc-p001-c001" in context
    assert "Evidence text." in context


def test_citation_verifier_rejects_unknown_source():
    answer = "This claim is supported. [Source 2]"
    sources = [{"chunk_id": "doc-p001-c001", "text": "This claim is supported."}]

    result = CitationVerifier().verify(answer, sources)

    assert result["valid"] is False
    assert result["invalid_citations"] == [2]


def test_citation_verifier_accepts_supported_source():
    answer = "This claim is supported by the evidence. [Source 1]"
    sources = [
        {
            "chunk_id": "doc-p001-c001",
            "text": "This claim is supported by the evidence.",
        }
    ]

    result = CitationVerifier().verify(answer, sources)

    assert result["valid"] is True
    assert result["valid_citations"] == [1]
