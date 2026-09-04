from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    char_count: int
    word_count: int
    checksum_sha256: str
    uploaded_at: str
    chunk_count: int = 0
    status: str = "indexed"  # processing, indexed, error
    extra_info: Optional[Dict[str, Any]] = None

class IngestionResponse(BaseModel):
    success: bool
    message: str
    document: Optional[DocumentMetadata] = None
    chunks_created: int = 0

class BatchIngestionResponse(BaseModel):
    success: bool
    total_uploaded: int
    documents: List[DocumentMetadata]
    errors: List[str] = []

class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    file_type: str
    chunk_index: int
    text: str
    char_length: int
    start_char: int
    end_char: int

class SearchQuery(BaseModel):
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of matching chunks to return")
    doc_id: Optional[str] = Field(default=None, description="Optional document ID filter")
    file_type: Optional[str] = Field(default=None, description="Optional file type filter (pdf, docx, csv, txt)")

class SearchHit(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    file_type: str
    chunk_index: int
    text: str
    similarity_score: float
    distance: float

class SearchResponse(BaseModel):
    query: str
    total_hits: int
    hits: List[SearchHit]

class AgentSpec(BaseModel):
    name: str
    milestone: str
    status: str
    responsibilities: List[str]
    inputs: List[str]
    outputs: List[str]

class ArchitectureInfo(BaseModel):
    system_name: str
    version: str
    rag_pipeline: Dict[str, Any]
    multi_agent_framework: List[AgentSpec]
