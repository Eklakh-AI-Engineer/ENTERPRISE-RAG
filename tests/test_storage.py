import pytest

from app.storage.in_memory import InMemoryDocumentStorage


def test_storage_round_trip():
    storage = InMemoryDocumentStorage()
    stored = storage.upload(path="org-a/doc-1/file.pdf", content=b"pdf", content_type="application/pdf")
    assert stored.size_bytes == 3
    assert storage.download(path=stored.path) == b"pdf"


def test_storage_rejects_traversal():
    storage = InMemoryDocumentStorage()
    with pytest.raises(ValueError):
        storage.upload(path="org-a/../secret.pdf", content=b"x", content_type="application/pdf")


def test_missing_object_is_explicit():
    storage = InMemoryDocumentStorage()
    with pytest.raises(FileNotFoundError):
        storage.download(path="missing.pdf")
