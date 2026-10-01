from __future__ import annotations

from typing import Any

from app.persistence.chunks import ChunkRepository, ChunkSearchResult
from app.persistence.entities import DocumentRecord


class SupabaseChunkRepository(ChunkRepository):
    """Tenant-safe chunk persistence adapter for pgvector-backed storage."""

    def __init__(self, client: Any, *, embedding_dimension: int = 384) -> None:
        self.client = client
        self.embedding_dimension = embedding_dimension

    def upsert_for_document(
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
                # PostgREST accepts pgvector values as vector literals. Keeping
                # serialization here avoids coupling the indexing pipeline to
                # a specific Supabase Python SDK version.
                "embedding": "[" + ",".join(str(float(value)) for value in embedding) + "]",
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


    def search_similar(
        self,
        *,
        organization_id: str,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[ChunkSearchResult]:
        if not organization_id.strip():
            raise ValueError("organization_id is required")
        if len(query_embedding) != self.embedding_dimension:
            raise ValueError("query embedding dimension does not match pgvector contract")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        response = self.client.rpc(
            "match_document_chunks",
            {
                "query_embedding": "[" + ",".join(str(float(v)) for v in query_embedding) + "]",
                "match_count": min(top_k, 200),
                "organization_id": organization_id,
            },
        ).execute()
        error = getattr(response, "error", None)
        if error:
            raise RuntimeError(str(error))
        return [ChunkSearchResult(
            id=row["id"], document_id=row["document_id"], chunk_id=row["chunk_id"],
            content=row["content"], page=row["page"], section=row.get("section"),
            start_char=row.get("start_char"), end_char=row.get("end_char"),
            similarity=float(row["similarity"]),
        ) for row in (getattr(response, "data", None) or [])]
