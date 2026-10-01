import numpy as np

from app.indexing.pipeline import DocumentIndexingPipeline
from app.persistence.entities import DocumentRecord


class FakeEmbeddings:
    model_name = "test-embedding"
    dimension = 3

    def encode(self, texts):
        return np.asarray([[1.0, 0.0, 0.0] for _ in texts], dtype="float32")


class FakeChunks:
    def __init__(self):
        self.calls = []

    def upsert_for_document(self, **kwargs):
        self.calls.append(kwargs)
        return len(kwargs["chunks"])


def test_indexing_persists_normalized_embedding_contract():
    chunks = FakeChunks()
    pipeline = DocumentIndexingPipeline(embeddings=FakeEmbeddings(), chunks=chunks)
    document = DocumentRecord(
        id="doc-1", organization_id="org-a", owner_user_id="user-a",
        filename="policy.pdf", storage_path="org-a/doc-1/policy.pdf",
        content_hash="hash", pipeline_version="v1",
    )
    result = pipeline.run(
        document=document,
        chunk_records=[{"chunk_id": "c1", "text": "alpha", "page": 1, "chunker_version": "v1"}],
    )
    assert result.chunk_count == 1
    assert result.embedding_dimension == 3
    assert chunks.calls[0]["embeddings"] == [[1.0, 0.0, 0.0]]


def test_indexing_rejects_embedding_count_mismatch():
    class BadEmbeddings(FakeEmbeddings):
        def encode(self, texts):
            return np.empty((0, 3), dtype="float32")

    pipeline = DocumentIndexingPipeline(embeddings=BadEmbeddings(), chunks=FakeChunks())
    document = DocumentRecord(
        id="doc-1", organization_id="org-a", owner_user_id="user-a",
        filename="policy.pdf", storage_path="x", content_hash="h", pipeline_version="v1",
    )
    try:
        pipeline.run(document=document, chunk_records=[{"text": "x"}])
    except ValueError as exc:
        assert "embedding count" in str(exc)
    else:
        raise AssertionError("expected mismatch failure")


def test_indexing_serialization_is_adapter_owned():
    from app.persistence.supabase_chunks import SupabaseChunkRepository

    class Response:
        error = None

    class Query:
        def upsert(self, rows, on_conflict=None):
            self.rows = rows
            self.on_conflict = on_conflict
            return self
        def execute(self):
            return Response()

    class Client:
        def __init__(self):
            self.query = Query()
        def table(self, _name):
            return self.query

    client = Client()
    repo = SupabaseChunkRepository(client, embedding_dimension=3)
    document = DocumentRecord(id="d", organization_id="o", owner_user_id="u", filename="x.pdf", storage_path="x", content_hash="h", pipeline_version="v")
    repo.upsert_for_document(document=document, chunks=[{"chunk_id":"c","text":"x","page":1,"chunker_version":"v"}], embeddings=[[1.0,0.0,0.0]], embedding_model="test")
    assert client.query.rows[0]["embedding"] == "[1.0,0.0,0.0]"
