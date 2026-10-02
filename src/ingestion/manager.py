"""
Ingestion Manager coordinating document parsing, normalization, metadata persistence, and batch processing.
"""
import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO, Union

from configs.settings import settings
from .base import (
    BaseParser,
    FileType,
    DocumentMetadata,
    ParsedDocument
)
from .parsers import PDFParser, DOCXParser, CSVParser, TXTParser

logger = logging.getLogger(__name__)


class IngestionManager:
    """Coordinates parsing, normalization, storage, and metadata management for all uploaded documents."""

    def __init__(
        self,
        uploads_dir: Optional[Path] = None,
        processed_dir: Optional[Path] = None,
        registry_file: Optional[Path] = None
    ):
        self.uploads_dir = uploads_dir or settings.UPLOADS_DIR
        self.processed_dir = processed_dir or settings.PROCESSED_DIR
        self.registry_file = registry_file or settings.DOCUMENTS_REGISTRY_FILE

        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        # Register parsers for each supported file type
        self._parsers: Dict[FileType, BaseParser] = {
            FileType.PDF: PDFParser(),
            FileType.DOCX: DOCXParser(),
            FileType.CSV: CSVParser(),
            FileType.TXT: TXTParser()
        }

        # Extension mapping
        self._extension_map: Dict[str, FileType] = {
            ".pdf": FileType.PDF,
            ".docx": FileType.DOCX,
            ".csv": FileType.CSV,
            ".txt": FileType.TXT,
            ".md": FileType.TXT,
            ".log": FileType.TXT
        }

        # Initialize or load document registry
        self._registry: Dict[str, DocumentMetadata] = self._load_registry()

    def _load_registry(self) -> Dict[str, DocumentMetadata]:
        """Loads persistent document metadata registry from disk."""
        if not self.registry_file.exists():
            return {}
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {doc_id: DocumentMetadata(**meta) for doc_id, meta in data.items()}
        except Exception as e:
            logger.error(f"Failed to load document registry from {self.registry_file}: {e}")
            return {}

    def _save_registry(self) -> None:
        """Persists document metadata registry to disk."""
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                data = {doc_id: meta.model_dump() for doc_id, meta in self._registry.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save document registry: {e}")

    def detect_file_type(self, filename: str) -> Optional[FileType]:
        """Detects FileType enum from filename extension."""
        suffix = Path(filename).suffix.lower()
        return self._extension_map.get(suffix)

    def save_uploaded_file(self, file_obj: BinaryIO, filename: str) -> Tuple[Path, str]:
        """
        Saves an uploaded file stream to the uploads directory with a unique document ID prefix.
        Returns (stored_path, document_id).
        """
        doc_id = str(uuid.uuid4())
        clean_filename = Path(filename).name
        stored_filename = f"{doc_id}_{clean_filename}"
        stored_path = self.uploads_dir / stored_filename

        with open(stored_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)

        return stored_path, doc_id

    def process_file(
        self,
        file_path: Path,
        original_filename: Optional[str] = None,
        custom_metadata: Optional[Dict] = None
    ) -> ParsedDocument:
        """
        Processes a single document file on disk:
        1. Validates file extension.
        2. Detects parser.
        3. Extracts and normalizes text.
        4. Updates document registry.
        5. Caches parsed text.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        orig_name = original_filename or file_path.name
        file_type = self.detect_file_type(orig_name)
        if not file_type:
            raise ValueError(f"Unsupported file type for {orig_name}. Supported: PDF, DOCX, CSV, TXT")

        parser = self._parsers.get(file_type)
        if not parser:
            raise ValueError(f"No parser available for file type {file_type}")

        # Compute hash and size
        file_hash = BaseParser.calculate_file_hash(file_path)
        file_stat = file_path.stat()
        doc_id = str(uuid.uuid4())

        metadata = DocumentMetadata(
            document_id=doc_id,
            filename=file_path.name,
            original_name=orig_name,
            file_type=file_type,
            file_size_bytes=file_stat.st_size,
            file_hash=file_hash,
            upload_timestamp=datetime.utcnow().isoformat() + "Z",
            custom_metadata=custom_metadata or {}
        )

        # Parse document
        parsed_doc = parser.parse(file_path, metadata=metadata)

        # Cache normalized text to processed dir
        processed_cache_file = self.processed_dir / f"{doc_id}.json"
        with open(processed_cache_file, "w", encoding="utf-8") as f:
            f.write(parsed_doc.model_dump_json(indent=2))

        # Register metadata
        self._registry[doc_id] = parsed_doc.metadata
        self._save_registry()

        return parsed_doc

    def process_batch(
        self,
        files: List[Tuple[Union[Path, BinaryIO], str]],
        custom_metadata: Optional[Dict] = None
    ) -> Tuple[List[ParsedDocument], List[Dict[str, str]]]:
        """
        Processes multiple uploaded documents in batch.
        Returns (successful_parsed_docs, errors_list).
        """
        successful: List[ParsedDocument] = []
        errors: List[Dict[str, str]] = []

        for file_item, filename in files:
            try:
                if isinstance(file_item, Path):
                    parsed = self.process_file(file_item, original_filename=filename, custom_metadata=custom_metadata)
                else:
                    stored_path, _ = self.save_uploaded_file(file_item, filename)
                    parsed = self.process_file(stored_path, original_filename=filename, custom_metadata=custom_metadata)
                successful.append(parsed)
            except Exception as e:
                logger.error(f"Failed batch ingestion for {filename}: {e}", exc_info=True)
                errors.append({
                    "filename": filename,
                    "error": str(e)
                })

        return successful, errors

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """Retrieves metadata for a given document ID."""
        return self._registry.get(document_id)

    def get_parsed_document(self, document_id: str) -> Optional[ParsedDocument]:
        """Retrieves full parsed document content from processed cache."""
        cache_file = self.processed_dir / f"{document_id}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ParsedDocument(**data)
        except Exception as e:
            logger.error(f"Failed to read cached parsed doc {document_id}: {e}")
            return None

    def list_documents(self) -> List[DocumentMetadata]:
        """Returns list of all ingested documents."""
        return list(self._registry.values())

    def update_document_chunk_count(self, document_id: str, chunk_count: int) -> None:
        """Updates the chunk count for a document in the registry."""
        if document_id in self._registry:
            self._registry[document_id].chunk_count = chunk_count
            self._registry[document_id].status = "indexed"
            self._save_registry()

    def delete_document(self, document_id: str) -> bool:
        """Removes a document from disk and registry."""
        if document_id not in self._registry:
            return False

        meta = self._registry.pop(document_id)
        self._save_registry()

        # Delete raw upload file if exists
        upload_path = self.uploads_dir / meta.filename
        if upload_path.exists():
            try:
                upload_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete upload file {upload_path}: {e}")

        # Delete processed cache
        cache_file = self.processed_dir / f"{document_id}.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
            except Exception as e:
                logger.warning(f"Could not delete cache file {cache_file}: {e}")

        return True
