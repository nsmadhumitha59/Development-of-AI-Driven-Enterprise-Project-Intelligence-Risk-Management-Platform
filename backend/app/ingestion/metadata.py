import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.schemas import DocumentMetadata
from app.config import settings

class MetadataStore:
    def __init__(self, store_path: str = settings.METADATA_STORE_PATH):
        self.store_path = Path(store_path)
        self._data: Dict[str, DocumentMetadata] = {}
        self._load()

    def _load(self):
        """Loads stored metadata from JSON file if present."""
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    for doc_id, meta in raw_data.items():
                        self._data[doc_id] = DocumentMetadata(**meta)
            except Exception as e:
                print(f"[MetadataStore] Warning: Failed to load metadata store ({e}). Starting fresh.")
                self._data = {}

    def _save(self):
        """Persists metadata to JSON file."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = {doc_id: meta.model_dump() for doc_id, meta in self._data.items()}
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)

    def add_document(self, meta: DocumentMetadata):
        """Add or update document metadata."""
        self._data[meta.doc_id] = meta
        self._save()

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Retrieve document metadata by doc_id."""
        return self._data.get(doc_id)

    def list_documents(self) -> List[DocumentMetadata]:
        """List all documents sorted by upload date descending."""
        return sorted(self._data.values(), key=lambda x: x.uploaded_at, reverse=True)

    def delete_document(self, doc_id: str) -> bool:
        """Remove document metadata entry."""
        if doc_id in self._data:
            del self._data[doc_id]
            self._save()
            return True
        return False

def generate_doc_metadata(
    filename: str,
    file_type: str,
    file_bytes: bytes,
    normalized_text: str,
    extra_info: Optional[Dict[str, Any]] = None
) -> DocumentMetadata:
    """Computes document hash, character counts, word counts, and constructs DocumentMetadata schema."""
    checksum = hashlib.sha256(file_bytes).hexdigest()
    doc_id = f"doc_{checksum[:12]}"
    
    char_count = len(normalized_text)
    word_count = len(normalized_text.split())
    uploaded_at = datetime.now(timezone.utc).isoformat()
    
    return DocumentMetadata(
        doc_id=doc_id,
        filename=filename,
        file_type=file_type,
        file_size_bytes=len(file_bytes),
        char_count=char_count,
        word_count=word_count,
        checksum_sha256=checksum,
        uploaded_at=uploaded_at,
        chunk_count=0,
        status="indexed",
        extra_info=extra_info or {}
    )

metadata_store = MetadataStore()
