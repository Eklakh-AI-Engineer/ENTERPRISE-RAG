from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth.service import AuthService, InvalidTokenError, SupabaseTokenVerifier
from app.config.settings import settings
from app.integrations.supabase import create_service_client, create_user_client
from app.persistence.supabase import SupabaseDocumentRepository, SupabaseIngestionJobRepository
from app.services.documents import DocumentService
from app.storage.supabase import SupabaseDocumentStorage
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


def current_user_client(authorization: str | None = Header(default=None)):
    principal = current_principal(authorization)
    try:
        _, _, token = authorization.partition(" ")
        return principal, create_user_client(access_token=token.strip())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Supabase client is not configured.") from exc


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


@app.post("/documents/upload")
async def upload_document(
    organization_id: str = Form(...),
    file: UploadFile = File(...),
    auth=Depends(current_user_client),
):
    principal, user_client = auth
    organization_id = organization_id.strip()
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id is required.")
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only application/pdf documents are supported.")

    membership = (
        user_client.table("organization_members")
        .select("organization_id")
        .eq("organization_id", organization_id)
        .eq("user_id", principal.user_id)
        .maybe_single()
        .execute()
    )
    if getattr(membership, "error", None):
        raise HTTPException(status_code=503, detail="Failed to verify organization membership.")
    if not getattr(membership, "data", None):
        raise HTTPException(status_code=403, detail="User is not a member of this organization.")

    content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the configured upload limit.")

    user_documents = SupabaseDocumentRepository(user_client)
    worker_jobs = SupabaseIngestionJobRepository(create_service_client())
    service = DocumentService(user_documents, worker_jobs)
    submission = service.submit(
        organization_id=organization_id,
        owner_user_id=principal.user_id,
        filename=file.filename or "document.pdf",
        content=content,
        pipeline_version=settings.INGESTION_PIPELINE_VERSION,
    )

    storage = SupabaseDocumentStorage(user_client, settings.SUPABASE_DOCUMENTS_BUCKET)
    if not submission.deduplicated:
        try:
            storage.upload(
                path=submission.document.storage_path,
                content=content,
                content_type="application/pdf",
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Document storage upload failed.") from exc

    return {
        "document_id": submission.document.id,
        "ingestion_job_id": submission.ingestion_job.id,
        "organization_id": submission.document.organization_id,
        "status": submission.document.status,
        "job_status": submission.ingestion_job.status,
        "deduplicated": submission.deduplicated,
    }


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
