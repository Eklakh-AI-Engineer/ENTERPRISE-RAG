from __future__ import annotations

from typing import Any

from app.config.settings import settings
from app.indexing.embeddings import SentenceTransformerEmbeddingProvider
from app.indexing.pipeline import DocumentIndexingPipeline
from app.ingestion.pipeline import PdfIngestionPipeline
from app.ingestion.worker import IngestionWorker, WorkerConfig
from app.persistence.supabase import SupabaseDocumentRepository, SupabaseIngestionJobRepository
from app.persistence.supabase_chunks import SupabaseChunkRepository
from app.storage.supabase import SupabaseDocumentStorage


def build_worker(client: Any, *, organization_id: str) -> IngestionWorker:
    """Compose the production worker from one trusted database client."""
    if not organization_id.strip():
        raise ValueError("organization_id is required")
    embeddings = SentenceTransformerEmbeddingProvider(settings.DENSE_MODEL)
    if embeddings.dimension != 384:
        raise ValueError("configured embedding model dimension does not match pgvector")
    return IngestionWorker(
        jobs=SupabaseIngestionJobRepository(client),
        documents=SupabaseDocumentRepository(client),
        storage=SupabaseDocumentStorage(client, settings.SUPABASE_DOCUMENTS_BUCKET),
        pipeline=PdfIngestionPipeline(),
        indexer=DocumentIndexingPipeline(
            embeddings=embeddings,
            chunks=SupabaseChunkRepository(client, embedding_dimension=384),
        ),
        config=WorkerConfig(lease_seconds=300),
    )
