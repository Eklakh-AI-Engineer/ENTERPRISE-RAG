from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.query.pipeline import QueryPipeline


pipeline: QueryPipeline | None = None


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Question to ask the Enterprise RAG system.",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline

    print("=" * 80)
    print("ENTERPRISE RAG API")
    print("=" * 80)
    print("Loading QueryPipeline...")

    pipeline = QueryPipeline(
        retrieval_top_k=settings.RETRIEVAL_TOP_K,
        rerank_top_k=settings.RERANK_TOP_K,
        candidate_k=settings.CANDIDATE_K,
    )

    print("QueryPipeline loaded successfully.")
    print("API ready.")

    yield

    print("Shutting down Enterprise RAG API...")


app = FastAPI(
    title="Enterprise RAG API",
    description=(
        "Evidence-grounded Enterprise RAG API providing "
        "hybrid retrieval, reranking, cited answers, "
        "evaluation metrics, and pipeline observability."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "enterprise-rag",
        "environment": settings.ENVIRONMENT,
        "pipeline_loaded": pipeline is not None,
    }


@app.post("/query")
def query(request: QueryRequest):
    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline is not loaded.",
        )

    query_text = request.query.strip()

    if not query_text:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )

    try:
        return pipeline.run(query_text)

    except Exception as exc:
        print("=" * 80)
        print("QUERY ERROR")
        print("=" * 80)
        print(exc)

        raise HTTPException(
            status_code=500,
            detail="Failed to process the query.",
        )
