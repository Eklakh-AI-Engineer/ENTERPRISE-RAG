from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth.service import AuthService, InvalidTokenError, SupabaseTokenVerifier
from app.config.settings import settings
from app.integrations.supabase import create_user_client
from app.query.pipeline import QueryPipeline


pipeline: QueryPipeline | None = None


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Question to ask the Enterprise RAG system.",
    )


class AuthMeResponse(BaseModel):
    user_id: str
    role: str


def _auth_service() -> AuthService:
    try:
        return AuthService(SupabaseTokenVerifier(create_user_client()))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Authentication service is not configured.") from exc


def current_principal(authorization: str | None = Header(default=None)):
    try:
        return _auth_service().authenticate_bearer(authorization)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or missing access token.") from exc


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
    allow_methods=["*"] ,
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


@app.get("/auth/me", response_model=AuthMeResponse)
def auth_me(principal=Depends(current_principal)):
    return AuthMeResponse(user_id=principal.user_id, role=principal.role)


@app.post("/query")
def query(request: QueryRequest):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline is not loaded.")

    query_text = request.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        return pipeline.run(query_text)
    except Exception as exc:
        print("QUERY ERROR")
        print(exc)
        raise HTTPException(status_code=500, detail="Failed to process the query.") from exc
