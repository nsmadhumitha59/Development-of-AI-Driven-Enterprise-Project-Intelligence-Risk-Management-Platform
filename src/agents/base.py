"""
Base Agent classes, data contracts, and grounding validation utilities for Milestone 2.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from src.architecture.system_design import RetrievedChunk


class AgentExecutionStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NO_DATA = "no_data"


class SourceReference(BaseModel):
    """Provenance tracking connecting an agent finding directly back to a RAG chunk."""
    chunk_id: str
    document_id: str
    filename: str
    file_type: str
    page_number: Optional[int] = None
    row_number: Optional[int] = None
    section_title: Optional[str] = None
    similarity_score: float = 0.0
    snippet: str


class BaseAgentResult(BaseModel):
    """Base response schema for all milestone agents."""
    agent_name: str
    agent_role: str
    execution_status: AgentExecutionStatus = AgentExecutionStatus.SUCCESS
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    retrieved_chunks_count: int = 0
    grounding_references: List[SourceReference] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    notes: Optional[str] = None


class BaseAgent(ABC):
    """Abstract Base Class for all specialized intelligence agents."""

    def __init__(self, name: str, role: str, description: str):
        self.name = name
        self.role = role
        self.description = description

    @abstractmethod
    def analyze(self, retrieval_chunks: List[RetrievedChunk], query_context: Optional[str] = None) -> BaseAgentResult:
        """
        Executes domain-specific analysis on retrieved RAG chunks.
        
        Args:
            retrieval_chunks: List of relevant chunks retrieved from vector store.
            query_context: Optional guiding user question or specific focus.
            
        Returns:
            Structured agent result.
        """
        pass

    @staticmethod
    def map_chunks_to_references(chunks: List[RetrievedChunk], max_refs: int = 10) -> List[SourceReference]:
        """Converts RetrievedChunk objects into clean, traceable SourceReference models."""
        references = []
        for c in chunks[:max_refs]:
            ref = SourceReference(
                chunk_id=c.chunk_id,
                document_id=c.metadata.document_id,
                filename=c.metadata.filename,
                file_type=c.metadata.file_type.value if hasattr(c.metadata.file_type, 'value') else str(c.metadata.file_type),
                page_number=c.metadata.page_number,
                row_number=c.metadata.row_number,
                section_title=c.metadata.section_title,
                similarity_score=c.score,
                snippet=c.content[:200] + ("..." if len(c.content) > 200 else "")
            )
            references.append(ref)
        return references
