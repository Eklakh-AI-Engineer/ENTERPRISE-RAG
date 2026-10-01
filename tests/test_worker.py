from app.ingestion.worker import IngestionWorker
from app.persistence.entities import DocumentRecord, IngestionJobRecord
from app.persistence.in_memory import InMemoryDocumentRepository, InMemoryIngestionJobRepository
from app.storage.in_memory import InMemoryDocumentStorage
from app.indexing.pipeline import IndexingResult


class FakePipeline:
    def run(self, **_kwargs):
        return type("Artifact", (), {"pages": [], "chunks": [{"chunk_id": "c1"}]})()


class FakeIndexer:
    def __init__(self):
        self.calls = []
    def run(self, *, document, chunk_records):
        self.calls.append((document.id, chunk_records))
        return IndexingResult(chunk_count=len(chunk_records), embedding_model="test", embedding_dimension=3)


def test_worker_processes_only_claimed_job():
    docs = InMemoryDocumentRepository()
    jobs = InMemoryIngestionJobRepository()
    storage = InMemoryDocumentStorage()
    indexer = FakeIndexer()
    document = DocumentRecord(
        id="doc-1", organization_id="org-a", owner_user_id="user-a", filename="a.pdf",
        storage_path="org-a/doc-1/a.pdf", content_hash="h", pipeline_version="v1",
        status="UPLOADED",
    )
    docs.save(document)
    storage.upload(path=document.storage_path, content=b"pdf", content_type="application/pdf")
    job = IngestionJobRecord(
        id="job-1", organization_id="org-a", document_id="doc-1",
        pipeline_version="v1", content_hash="h", status="PROCESSING",
    )
    jobs.create(job)
    worker = IngestionWorker(
        jobs=jobs, documents=docs, storage=storage, pipeline=FakePipeline(), indexer=indexer
    )
    result = worker.process_claimed(job)
    assert result.status == "READY"
    assert indexer.calls == [("doc-1", [{"chunk_id": "c1"}])]
    assert document.status == "READY"
    assert document.page_count == 0


def test_worker_factory_builds_all_production_boundaries(monkeypatch):
    import app.ingestion.factory as factory

    class FakeEmbeddings:
        dimension = 384
        model_name = "test"

    monkeypatch.setattr(factory, "SentenceTransformerEmbeddingProvider", lambda _: FakeEmbeddings())
    worker = factory.build_worker(object(), organization_id="org-a")
    assert worker.config.lease_seconds == 300
    assert worker.pipeline is not None
    assert worker.indexer is not None
