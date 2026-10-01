import os

from dotenv import load_dotenv

load_dotenv()


def _csv_env(name: str, default: str) -> list[str]:
    return [
        value.strip()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    ]


class Settings:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    DENSE_INDEX_PATH = os.getenv(
        "DENSE_INDEX_PATH",
        "data/processed/dense.index",
    )

    DENSE_METADATA_PATH = os.getenv(
        "DENSE_METADATA_PATH",
        "data/processed/dense_metadata.json",
    )

    BM25_METADATA_PATH = os.getenv(
        "BM25_METADATA_PATH",
        "data/processed/bm25_metadata.json",
    )

    DENSE_MODEL = os.getenv(
        "DENSE_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )

    RERANKER_MODEL = os.getenv(
        "RERANKER_MODEL",
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
    )

    RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "10"))
    RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))
    CANDIDATE_K = int(os.getenv("CANDIDATE_K", "10"))

    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "8000"))

    CORS_ORIGINS = _csv_env(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_DOCUMENTS_BUCKET = os.getenv("SUPABASE_DOCUMENTS_BUCKET", "documents")


settings = Settings()
