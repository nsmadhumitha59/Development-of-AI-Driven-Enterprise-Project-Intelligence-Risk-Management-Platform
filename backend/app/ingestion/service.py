import os
from pathlib import Path
from typing import Tuple, Dict, Any
from app.config import settings
from app.ingestion.extractors import extract_content
from app.ingestion.normalizer import normalize_text
from app.ingestion.metadata import generate_doc_metadata, metadata_store
from app.schemas import DocumentMetadata

class IngestionService:
    def __init__(self, upload_dir: str = settings.UPLOAD_DIR):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def process_file(self, filename: str, file_bytes: bytes) -> Tuple[DocumentMetadata, str]:
        """
        Processes uploaded document file:
        1. Extract text & file type using format extractors.
        2. Normalize text content.
        3. Compute SHA256 & generate DocumentMetadata.
        4. Save original file to uploads directory.
        5. Persist metadata.
        Returns (DocumentMetadata, normalized_text).
        """
        # 1. Extract content
        raw_text, file_type, extra_meta = extract_content(file_bytes, filename)
        
        # 2. Normalize text
        normalized_text = normalize_text(raw_text)
        
        # 3. Generate Metadata
        metadata = generate_doc_metadata(
            filename=filename,
            file_type=file_type,
            file_bytes=file_bytes,
            normalized_text=normalized_text,
            extra_info=extra_meta
        )
        
        # 4. Save file to disk
        saved_filepath = self.upload_dir / f"{metadata.doc_id}_{filename}"
        with open(saved_filepath, "wb") as f:
            f.write(file_bytes)
            
        # 5. Save metadata
        metadata_store.add_document(metadata)
        
        return metadata, normalized_text

ingestion_service = IngestionService()
