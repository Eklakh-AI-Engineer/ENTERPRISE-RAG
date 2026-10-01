from __future__ import annotations

from typing import Any

from app.persistence.chunks import ChunkRepository
from app.persistence.entities import DocumentRecord


class SupabaseChunkRepository(ChunkRepository):
    """Tenant-safe chunk persistence adapter for pgvector-backed storage."""

    def __init__(self, client: Any, *, embedding_dimension: int = 384) -> None:
        self.client = client
        self.embedding_dimension = embedding_dimension

    def replace_for_document(
        self,
        *,
        document: DocumentRecord,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        embedding_model: str,
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunk and embedding counts must match")
        rows: list[dict[str, Any]] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            if len(embedding) != self.embedding_dimension:
                raise ValueError("embedding dimension does not match pgvector contract")
            rows.append({
                "document_id": document.id,
                "chunk_id": chunk["chunk_id"],
                "content": chunk["text"],
                "page": chunk["page"],
                "section": chunk.get("section"),
                "start_char": chunk.get("start_char"),
                "end_char": chunk.get("end_char"),
                "chunker_version": chunk["chunker_version"],
                "embedding_model": embedding_model,
                "embedding_dimension": self.embedding_dimension,
                "embedding": embedding,
                "metadata": {
                    "source": chunk.get("source"),
                    "doc_type": chunk.get("doc_type"),
                    "chunk_index": chunk.get("chunk_index"),
                },
            })
        if not rows:
            return 0
        response = (
            self.client.table("document_chunks")
            .upsert(rows, on_conflict="document_id,chunk_id,chunker_version")
            .execute()
        )
        error = getattr(response, "error", None)
        if error:
            raise RuntimeError(str(error))
        return len(rows)
