from app.ingestion.pipeline import IngestionArtifact, PdfIngestionPipeline


def test_pdf_pipeline_preserves_document_identity_and_spans():
    def fake_parser(_path):
        return [{
            "document_id": "filename-stem",
            "source": "policy.pdf",
            "page": 1,
            "doc_type": "pdf",
            "text": "alpha beta gamma",
            "parser_version": "test-parser",
        }]

    class FakeChunker:
        VERSION = "test-chunker"
        def chunk_pages(self, pages):
            assert pages[0]["document_id"] == "doc-123"
            return [{"chunk_id": "doc-123-p001-c001", "start_char": 0, "end_char": 5}]

    artifact = PdfIngestionPipeline(parser=fake_parser, chunker=FakeChunker()).run(
        content=b"not-really-a-pdf", filename="policy.pdf", document_id="doc-123"
    )
    assert isinstance(artifact, IngestionArtifact)
    assert artifact.parser_version == "test-parser"
    assert artifact.chunker_version == "test-chunker"
    assert artifact.chunks[0]["chunk_id"] == "doc-123-p001-c001"
