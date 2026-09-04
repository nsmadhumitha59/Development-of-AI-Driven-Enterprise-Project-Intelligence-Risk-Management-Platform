import os
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.schemas import (
    DocumentMetadata,
    IngestionResponse,
    BatchIngestionResponse,
    SearchQuery,
    SearchResponse,
    ArchitectureInfo
)
from app.ingestion.service import ingestion_service
from app.ingestion.metadata import metadata_store
from app.rag.service import rag_service
from app.agents.specs import get_system_architecture_info

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Milestone 1 REST API for Document Ingestion and RAG Semantic Retrieval"
)

# Enable CORS for Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/system/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "indexed_documents": len(metadata_store.list_documents())
    }

@app.get("/api/v1/system/architecture", response_model=ArchitectureInfo, tags=["System"])
def get_architecture():
    """Returns overall system architecture design, RAG pipeline details, and multi-agent structure."""
    return get_system_architecture_info()

@app.post("/api/v1/documents/upload", response_model=BatchIngestionResponse, tags=["Document Ingestion"])
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload and process one or more documents (PDF, DOCX, CSV, TXT).
    Pipeline: Content Extraction -> Normalization -> Metadata Generation -> Chunking -> Vector Embedding -> Persistent Indexing.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    processed_docs: List[DocumentMetadata] = []
    errors: List[str] = []

    for file in files:
        try:
            content = await file.read()
            if not content:
                errors.append(f"File '{file.filename}' is empty.")
                continue

            # 1. Ingest document (Extraction + Normalization + Metadata)
            metadata, normalized_text = ingestion_service.process_file(file.filename, content)

            # 2. Index in RAG Pipeline (Chunking + SentenceTransformers + ChromaDB)
            chunks_created = rag_service.index_document(metadata, normalized_text)

            processed_docs.append(metadata)

        except Exception as e:
            errors.append(f"Error processing '{file.filename}': {str(e)}")

    return BatchIngestionResponse(
        success=len(processed_docs) > 0,
        total_uploaded=len(processed_docs),
        documents=processed_docs,
        errors=errors
    )

@app.get("/api/v1/documents", response_model=List[DocumentMetadata], tags=["Document Ingestion"])
def list_documents():
    """List all uploaded document metadata records."""
    return metadata_store.list_documents()

@app.get("/api/v1/documents/{doc_id}", response_model=DocumentMetadata, tags=["Document Ingestion"])
def get_document(doc_id: str):
    """Retrieve metadata for a specific document by doc_id."""
    doc = metadata_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{doc_id}' not found.")
    return doc

@app.delete("/api/v1/documents/{doc_id}", tags=["Document Ingestion"])
def delete_document(doc_id: str):
    """Delete a document and remove all its vector chunks from the database."""
    doc = metadata_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{doc_id}' not found.")

    success = rag_service.delete_document(doc_id)
    return {"success": success, "message": f"Document '{doc.filename}' ({doc_id}) deleted successfully."}

@app.post("/api/v1/rag/search", response_model=SearchResponse, tags=["RAG Pipeline"])
def search_documents(query_body: SearchQuery):
    """
    Perform semantic similarity search over indexed document chunks.
    Returns top-k matching chunks with similarity scores and source metadata.
    """
    return rag_service.search(
        query=query_body.query,
        top_k=query_body.top_k,
        doc_id=query_body.doc_id,
        file_type=query_body.file_type
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
