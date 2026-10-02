"""
Pydantic API request and response models for Milestone 1 endpoints.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from src.ingestion.base import DocumentMetadata, FileType


class UploadDocumentResult(BaseModel):
    document_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    page_count: Optional[int] = None
    row_count: Optional[int] = None
    char_count: int
    chunk_count: int
    status: str
    message: str


class DocumentUploadResponse(BaseModel):
    success: bool
    document: UploadDocumentResult


class BatchUploadResponse(BaseModel):
    success: bool
    total_processed: int
    successful_count: int
    failed_count: int
    documents: List[UploadDocumentResult]
    errors: List[Dict[str, str]] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    total_documents: int
    documents: List[DocumentMetadata]


class DocumentDetailResponse(BaseModel):
    metadata: DocumentMetadata
    preview_text: str
    total_sections: int


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Max number of results to return")
    document_id: Optional[str] = Field(default=None, description="Filter search to specific document ID")
    file_type: Optional[str] = Field(default=None, description="Filter search to specific file type (pdf, docx, csv, txt)")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold")


class QueryResultItem(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    file_type: str
    chunk_index: int
    content: str
    score: float
    page_number: Optional[int] = None
    row_number: Optional[int] = None
    section_title: Optional[str] = None
    token_estimate: int
    timestamp: str


class QueryResponse(BaseModel):
    query: str
    total_results: int
    results: List[QueryResultItem]
    execution_time_ms: float


class SystemHealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    milestone: int
    total_documents: int
    total_chunks: int
    embedding_model: str
    vector_store: str
    supported_file_types: List[str]


class MessageResponse(BaseModel):
    success: bool
    message: str
