from fastapi import FastAPI
from pydantic import BaseModel

from app.query.pipeline import QueryPipeline


app = FastAPI(
    title="Enterprise RAG API",
    description="Enterprise Retrieval-Augmented Generation API",
    version="1.0.0",
)


class QueryRequest(BaseModel):
    query: str


class Citation(BaseModel):
    source: int
    document: str
    page: int | None
    chunk_id: str


class Evaluation(BaseModel):
    citation_score: float
    relevance_score: float
    support_score: float
    overall_score: float
    total_citations: int
    valid_citations: list[int]
    invalid_citations: list[int]
    passed: bool


class Metrics(BaseModel):
    retrieval_ms: float
    reranking_ms: float
    generation_ms: float
    evaluation_ms: float
    total_ms: float

    retrieved_count: int
    reranked_count: int

    citation_score: float
    relevance_score: float
    support_score: float
    overall_score: float


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation]

    retrieved_count: int
    reranked_count: int

    evaluation: Evaluation
    metrics: Metrics


pipeline = QueryPipeline(
    retrieval_top_k=10,
    rerank_top_k=5,
    candidate_k=10,
)


@app.get("/")
def root():
    return {
        "service": "Enterprise RAG API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post(
    "/query",
    response_model=QueryResponse,
)
def query(request: QueryRequest):

    result = pipeline.run(request.query)

    return {
        "query": request.query,
        "answer": result["answer"],
        "citations": result["citations"],
        "retrieved_count": result["retrieved_count"],
        "reranked_count": result["reranked_count"],
        "evaluation": result["evaluation"],
        "metrics": result["metrics"],
    }