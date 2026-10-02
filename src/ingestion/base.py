"""
Base classes and data models for document parsing and ingestion.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import hashlib
import uuid


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    CSV = "csv"
    TXT = "txt"


class DocumentMetadata(BaseModel):
    """Metadata describing an ingested document."""
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_name: str
    file_type: FileType
    file_size_bytes: int
    file_hash: str
    upload_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    page_count: Optional[int] = None
    row_count: Optional[int] = None
    char_count: int = 0
    word_count: int = 0
    chunk_count: int = 0
    status: str = "uploaded"  # uploaded, parsed, indexed, failed
    error_message: Optional[str] = None
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentSection(BaseModel):
    """A logical section within a parsed document (e.g. a page, row, or heading)."""
    section_index: int
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    row_number: Optional[int] = None
    raw_text: str
    normalized_text: str = ""


class ParsedDocument(BaseModel):
    """Result of parsing and normalizing a raw document."""
    metadata: DocumentMetadata
    raw_text: str
    normalized_text: str
    sections: List[DocumentSection] = Field(default_factory=list)


class BaseParser(ABC):
    """Abstract Base Class for all document parsers."""
    
    @property
    @abstractmethod
    def supported_type(self) -> FileType:
        """Returns the file type supported by this parser."""
        pass

    @abstractmethod
    def parse(self, file_path: Path, metadata: Optional[DocumentMetadata] = None) -> ParsedDocument:
        """
        Parses a document file and returns a ParsedDocument containing raw and normalized text.
        
        Args:
            file_path: Absolute or relative Path to the file on disk.
            metadata: Optional pre-constructed DocumentMetadata.
            
        Returns:
            ParsedDocument with extracted sections and text.
        """
        pass

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Computes SHA-256 hash of a file for deduplication and integrity check."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
