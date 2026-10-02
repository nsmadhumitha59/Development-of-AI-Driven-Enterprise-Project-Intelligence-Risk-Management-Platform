"""
FastAPI Route Handlers for Document Ingestion and RAG Semantic Retrieval.
"""
import time
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, status

from configs.settings import settings
from src.ingestion.manager import IngestionManager
from src.rag.retriever import SemanticRetriever
from src.rag.embeddings import EmbeddingService
from src.rag.vectorstore import ChromaVectorStore
from .schemas import (
    DocumentUploadResponse,
    BatchUploadResponse,
    UploadDocumentResult,
    DocumentListResponse,
    DocumentDetailResponse,
    QueryRequest,
    QueryResponse,
    QueryResultItem,
    SystemHealthResponse,
    MessageResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Milestone 1 - Ingestion & RAG"])

# Global module instances
ingestion_mgr = IngestionManager()
embedding_svc = EmbeddingService.get_instance()
vector_store = ChromaVectorStore()
retriever = SemanticRetriever(
    vector_store=vector_store,
    embedding_service=embedding_svc
)


@router.post(
    "/documents/upload",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Index Documents",
    description="Accepts one or more documents (PDF, DOCX, CSV, TXT), extracts content, chunks it, generates embeddings, and indexes into ChromaDB."
)
async def upload_documents(
    files: List[UploadFile] = File(..., description="One or more files to ingest (PDF, DOCX, CSV, TXT)")
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload."
        )

    processed_results: List[UploadDocumentResult] = []
    errors: List[dict] = []

    for upload_file in files:
        filename = upload_file.filename or "unknown"
        # Validate extension
        detected_type = ingestion_mgr.detect_file_type(filename)
        if not detected_type:
            errors.append({
                "filename": filename,
                "error": f"Unsupported file type. Supported extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            })
            continue

        try:
            # 1. Save uploaded file
            stored_path, doc_id = ingestion_mgr.save_uploaded_file(upload_file.file, filename)
            
            # 2. Extract & normalize text
            parsed_doc = ingestion_mgr.process_file(stored_path, original_filename=filename)
            
            # 3. Chunk, embed, and store in vector database
            chunks = retriever.index_document(parsed_doc)
            ingestion_mgr.update_document_chunk_count(parsed_doc.metadata.document_id, len(chunks))

            processed_results.append(
                UploadDocumentResult(
                    document_id=parsed_doc.metadata.document_id,
                    filename=filename,
                    file_type=parsed_doc.metadata.file_type.value,
                    file_size_bytes=parsed_doc.metadata.file_size_bytes,
                    page_count=parsed_doc.metadata.page_count,
                    row_count=parsed_doc.metadata.row_count,
                    char_count=parsed_doc.metadata.char_count,
                    chunk_count=len(chunks),
                    status="indexed",
                    message=f"Successfully extracted, chunked ({len(chunks)} chunks), embedded, and indexed."
                )
            )
        except Exception as e:
            logger.error(f"Error processing upload for {filename}: {e}", exc_info=True)
            errors.append({
                "filename": filename,
                "error": str(e)
            })

    total_requested = len(files)
    success_count = len(processed_results)

    if success_count == 0 and errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "All document uploads failed.", "errors": errors}
        )

    return BatchUploadResponse(
        success=(success_count > 0),
        total_processed=total_requested,
        successful_count=success_count,
        failed_count=len(errors),
        documents=processed_results,
        errors=errors
    )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List All Ingested Documents",
    description="Returns metadata of all ingested documents stored in the registry."
)
async def list_documents():
    docs = ingestion_mgr.list_documents()
    return DocumentListResponse(
        total_documents=len(docs),
        documents=docs
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get Document Details & Content Preview"
)
async def get_document(document_id: str):
    meta = ingestion_mgr.get_document(document_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    parsed_doc = ingestion_mgr.get_parsed_document(document_id)
    preview = parsed_doc.normalized_text[:1000] + ("..." if len(parsed_doc.normalized_text) > 1000 else "") if parsed_doc else ""
    total_sections = len(parsed_doc.sections) if parsed_doc else 0

    return DocumentDetailResponse(
        metadata=meta,
        preview_text=preview,
        total_sections=total_sections
    )


@router.delete(
    "/documents/{document_id}",
    response_model=MessageResponse,
    summary="Delete Document and Vectors"
)
async def delete_document(document_id: str):
    meta = ingestion_mgr.get_document(document_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    # 1. Delete from vector DB
    retriever.delete_document_index(document_id)
    # 2. Delete from file storage and registry
    ingestion_mgr.delete_document(document_id)

    return MessageResponse(
        success=True,
        message=f"Document '{meta.original_name}' (ID: {document_id}) and all its vector embeddings were deleted."
    )


@router.post(
    "/rag/query",
    response_model=QueryResponse,
    summary="Execute Semantic Retrieval Query",
    description="Embeds search query and retrieves top-k most relevant document chunks with similarity scores and metadata."
)
async def query_rag(request: QueryRequest):
    start_time = time.perf_counter()

    try:
        retrieved_chunks = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
            file_type=request.file_type,
            min_score=request.min_score
        )
    except Exception as e:
        logger.error(f"Semantic retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval query failed: {str(e)}"
        )

    results = []
    for r in retrieved_chunks:
        results.append(
            QueryResultItem(
                chunk_id=r.chunk_id,
                document_id=r.metadata.document_id,
                filename=r.metadata.filename,
                file_type=r.metadata.file_type.value,
                chunk_index=r.metadata.chunk_index,
                content=r.content,
                score=r.score,
                page_number=r.metadata.page_number,
                row_number=r.metadata.row_number,
                section_title=r.metadata.section_title,
                token_estimate=r.metadata.token_estimate,
                timestamp=r.metadata.timestamp
            )
        )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return QueryResponse(
        query=request.query,
        total_results=len(results),
        results=results,
        execution_time_ms=elapsed_ms
    )


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="System Health & Stats"
)
async def get_health():
    stats = vector_store.get_stats()
    docs = ingestion_mgr.list_documents()

    return SystemHealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        milestone=1,
        total_documents=len(docs),
        total_chunks=stats.get("total_chunks_indexed", 0),
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        vector_store="ChromaDB (Persistent)",
        supported_file_types=list(settings.ALLOWED_EXTENSIONS)
    )
