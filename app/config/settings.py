import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
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

    RETRIEVAL_TOP_K = int(
        os.getenv("RETRIEVAL_TOP_K", "10")
    )

    RERANK_TOP_K = int(
        os.getenv("RERANK_TOP_K", "5")
    )

    CANDIDATE_K = int(
        os.getenv("CANDIDATE_K", "10")
    )


settings = Settings()