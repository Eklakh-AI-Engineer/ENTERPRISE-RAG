from __future__ import annotations

from app.storage.base import StoredObject


class InMemoryDocumentStorage:
    """Deterministic storage adapter used by service and worker tests."""

    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}

    def upload(self, *, path: str, content: bytes, content_type: str) -> StoredObject:
        if not path or path.startswith("/") or ".." in path.split("/"):
            raise ValueError("storage path must be relative and traversal-safe")
        if not content:
            raise ValueError("cannot upload empty content")
        self._objects[path] = (bytes(content), content_type)
        return StoredObject(path=path, content_type=content_type, size_bytes=len(content))

    def download(self, *, path: str) -> bytes:
        try:
            return self._objects[path][0]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc

    def delete(self, *, path: str) -> None:
        self._objects.pop(path, None)
