"""
FastAPI server for AI Command Center
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from agents.manager import ManagerAgent
from services.document_service import DocumentService
from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("AI Command Center API starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    yield
    # Shutdown
    logger.info("AI Command Center API shutting down...")


# Initialize FastAPI
app = FastAPI(
    title="AI Command Center API",
    description="Multi-agent AI system with manager orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize singletons
manager_agent = None
document_service = None


def get_manager() -> ManagerAgent:
    """Get or create manager agent instance"""
    global manager_agent
    if manager_agent is None:
        manager_agent = ManagerAgent()
    return manager_agent


def get_document_service() -> DocumentService:
    """Get or create document service instance"""
    global document_service
    if document_service is None:
        document_service = DocumentService(persist_directory=settings.VECTOR_DB_PATH)
    return document_service


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify API key from Authorization header"""
    api_key = credentials.credentials

    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return api_key


# Request/Response models
class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    answer: str
    metadata: Dict[str, Any]
    success: bool


class HealthResponse(BaseModel):
    status: str
    version: str


# Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Execute AI query through manager agent

    Requires:
    - Authorization header with API key
    - query: User's question/request
    - context: Optional context data
    """
    try:
        manager = get_manager()

        # Execute query
        result = await manager.execute(
            task=request.query,
            context=request.context
        )

        return {
            "answer": result["answer"],
            "metadata": result.get("metadata", {}),
            "success": result.get("success", True)
        }

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )


@app.get("/stats")
async def stats(api_key: str = Depends(verify_api_key)):
    """Get usage statistics"""
    try:
        manager = get_manager()

        # Collect stats from all agents
        all_stats = {
            "manager": manager.get_stats(),
            "specialists": {
                name: agent.get_stats()
                for name, agent in manager.agents.items()
            }
        }

        return all_stats

    except Exception as e:
        logger.error(f"Stats failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


# Document management endpoints
@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Upload and index a document

    Supported formats: PDF, TXT, MD
    """
    # Validate file type
    allowed_extensions = {".pdf", ".txt", ".md"}
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Read file content
        content = await file.read()

        # Get document service and ingest
        doc_service = get_document_service()
        result = await doc_service.ingest_document(
            content=content,
            filename=file.filename
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to process document")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@app.get("/documents")
async def list_documents(api_key: str = Depends(verify_api_key)):
    """List all indexed documents"""
    try:
        doc_service = get_document_service()
        sources = doc_service.list_sources()
        stats = doc_service.get_stats()

        return {
            "sources": sources,
            "total_chunks": stats["total_documents"],
            "total_files": len(sources)
        }

    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@app.delete("/documents/{source}")
async def delete_document(
    source: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete a document from the index"""
    try:
        doc_service = get_document_service()
        result = doc_service.delete_source(source)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to delete document")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@app.post("/documents/search")
async def search_documents(
    query: str,
    n_results: int = 5,
    api_key: str = Depends(verify_api_key)
):
    """Search indexed documents"""
    try:
        doc_service = get_document_service()
        results = doc_service.search(query=query, n_results=n_results)

        return {
            "query": query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Document search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


# Run with: uv run uvicorn api.main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )