from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.query.pipeline import QueryPipeline


# ---------------------------------------------------------
# Global pipeline
# ---------------------------------------------------------

pipeline: QueryPipeline | None = None


# ---------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Question to ask the Enterprise RAG system.",
    )


# ---------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    global pipeline

    print("=" * 80)
    print("ENTERPRISE RAG API")
    print("=" * 80)

    print("Loading QueryPipeline...")

    pipeline = QueryPipeline(
        retrieval_top_k=10,
        rerank_top_k=5,
        candidate_k=10,
    )

    print("QueryPipeline loaded successfully.")
    print("API ready.")

    yield

    print("Shutting down Enterprise RAG API...")


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="Enterprise RAG API",
    description=(
        "Evidence-grounded Enterprise RAG API providing "
        "hybrid retrieval, reranking, cited answers, "
        "evaluation metrics, and pipeline observability."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "enterprise-rag",
        "pipeline_loaded": pipeline is not None,
    }


# ---------------------------------------------------------
# Query endpoint
# ---------------------------------------------------------

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

        result = pipeline.run(query_text)

        return result

    except Exception as exc:

        print("=" * 80)
        print("QUERY ERROR")
        print("=" * 80)
        print(exc)

        raise HTTPException(
            status_code=500,
            detail="Failed to process the query.",
        )