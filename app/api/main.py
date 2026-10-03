from contextlib import asynccontextmanager
import logging
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth.service import AuthService, InvalidTokenError, SupabaseTokenVerifier
from app.config.settings import settings
from app.integrations.supabase import create_user_client
from app.persistence.supabase import SupabaseDocumentRepository, SupabaseIngestionJobRepository
from app.services.documents import DocumentService, DocumentValidationError
from app.storage.supabase import SupabaseDocumentStorage, SupabaseStorageError
from app.query.production import ProductionQueryPipeline


pipeline: ProductionQueryPipeline | None = None
logger = logging.getLogger("enterprise_rag.api")


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


class DocumentUploadResponse(BaseModel):
    document_id: str
    ingestion_job_id: str
    organization_id: str
    filename: str
    storage_path: str
    status: str
    deduplicated: bool


def _auth_service(token: str) -> AuthService:
    try:
        client = create_user_client(access_token=token)
        return AuthService(SupabaseTokenVerifier(client))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Authentication service is not configured.",
        ) from exc


def current_principal(
    authorization: str | None = Header(default=None),
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing access token.",
        )
    _, _, token = authorization.partition(" ")
    try:
        return _auth_service(token.strip()).authenticate_bearer(authorization)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or missing access token.") from exc


def current_user_client(authorization: str | None = Header(default=None)):
    principal = current_principal(authorization)
    try:
        _, _, token = authorization.partition(" ")
        return principal, create_user_client(access_token=token.strip())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Supabase client is not configured.") from exc


def _current_organization(client, user_id: str) -> str:
    response = (
        client.table("organization_members")
        .select("organization_id")
        .eq("user_id", user_id)
        .execute()
    )
    error = getattr(response, "error", None)
    if error:
        raise HTTPException(status_code=500, detail="Failed to resolve organization membership.")
    rows = getattr(response, "data", None) or []
    if len(rows) != 1:
        raise HTTPException(
            status_code=409,
            detail="The authenticated user must belong to exactly one organization for document upload.",
        )
    organization_id = rows[0].get("organization_id")
    if not isinstance(organization_id, str) or not organization_id:
        raise HTTPException(status_code=500, detail="Invalid organization membership record.")
    return organization_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline

    print("=" * 80)
    print("ENTERPRISE RAG API")
    print("=" * 80)
    print("Loading QueryPipeline...")

    pipeline = ProductionQueryPipeline(
        embedding_model=settings.DENSE_MODEL,
        reranker_model=settings.RERANKER_MODEL,
        retrieval_top_k=settings.RETRIEVAL_TOP_K,
        rerank_top_k=settings.RERANK_TOP_K,
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


@app.get("/ready")
def readiness():
    if pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline is not loaded.")
    return {
        "status": "ready",
        "service": "enterprise-rag",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/auth/me", response_model=AuthMeResponse)
def auth_me(principal=Depends(current_principal)):
    return AuthMeResponse(user_id=principal.user_id, role=principal.role)


@app.post("/documents", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    auth=Depends(current_user_client),
):
    principal, client = auth
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF documents are supported.")

    content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the upload size limit.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Uploaded file is not a valid PDF payload.")

    organization_id = _current_organization(client, principal.user_id)
    documents = SupabaseDocumentRepository(client)
    jobs = SupabaseIngestionJobRepository(client)
    storage = SupabaseDocumentStorage(client, settings.SUPABASE_DOCUMENTS_BUCKET)
    service = DocumentService(documents, jobs)

    try:
        submission = service.submit(
            organization_id=organization_id,
            owner_user_id=principal.user_id,
            filename=filename,
            content=content,
            pipeline_version=settings.INGESTION_PIPELINE_VERSION,
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        request_id = uuid4().hex[:12]
        logger.exception(
            "document_submission_failed request_id=%s user_id=%s organization_id=%s",
            request_id,
            principal.user_id,
            organization_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create document ingestion job. Reference: {request_id}",
        ) from exc

    if not submission.deduplicated:
        try:
            storage.upload(
                path=submission.document.storage_path,
                content=content,
                content_type="application/pdf",
            )
        except SupabaseStorageError as exc:
            try:
                jobs.client.table("ingestion_jobs").delete().eq(
                    "id", submission.ingestion_job.id
                ).eq("organization_id", organization_id).execute()
                documents.client.table("documents").delete().eq(
                    "id", submission.document.id
                ).eq("organization_id", organization_id).execute()
            except Exception:
                pass
            raise HTTPException(status_code=502, detail="Failed to upload document to storage.") from exc

    return DocumentUploadResponse(
        document_id=submission.document.id,
        ingestion_job_id=submission.ingestion_job.id,
        organization_id=organization_id,
        filename=submission.document.filename,
        storage_path=submission.document.storage_path,
        status=submission.document.status,
        deduplicated=submission.deduplicated,
    )


@app.get("/documents/{document_id}", response_model=DocumentUploadResponse)
def get_document(
    document_id: str,
    auth=Depends(current_user_client),
):
    principal, client = auth
    try:
        organization_id = _current_organization(client, principal.user_id)
        documents = SupabaseDocumentRepository(client)
        jobs = SupabaseIngestionJobRepository(client)
        document = documents.get(document_id, organization_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        job = jobs.get_by_document(document.id, organization_id)
        if job is None:
            raise HTTPException(status_code=409, detail="Document ingestion job not found.")
        return DocumentUploadResponse(
            document_id=document.id,
            ingestion_job_id=job.id,
            organization_id=organization_id,
            filename=document.filename,
            storage_path=document.storage_path,
            status=document.status,
            deduplicated=False,
        )
    except HTTPException:
        raise
    except Exception as exc:
        request_id = uuid4().hex[:12]
        logger.exception(
            "document_status_failed request_id=%s user_id=%s organization_id=%s document_id=%s",
            request_id,
            principal.user_id,
            organization_id,
            document_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read document status. Reference: {request_id}",
        ) from exc


@app.post("/query")
def query(request: QueryRequest, auth=Depends(current_user_client)):
    if pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline is not loaded.")

    principal, client = auth
    query_text = request.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        organization_id = _current_organization(client, principal.user_id)
        return pipeline.run(
            query=query_text,
            organization_id=organization_id,
            client=client,
        )
    except HTTPException:
        raise
    except Exception as exc:
        request_id = uuid4().hex[:12]
        logger.exception(
            "query_failed request_id=%s user_id=%s organization_id=%s",
            request_id,
            principal.user_id,
            organization_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process the query. Reference: {request_id}",
        ) from exc
