from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredObject:
    path: str
    content_type: str
    size_bytes: int


class DocumentStorage(Protocol):
    """Application boundary for source-document object storage."""

    def upload(
        self,
        *,
        path: str,
        content: bytes,
        content_type: str,
    ) -> StoredObject: ...

    def download(self, *, path: str) -> bytes: ...

    def delete(self, *, path: str) -> None: ...
