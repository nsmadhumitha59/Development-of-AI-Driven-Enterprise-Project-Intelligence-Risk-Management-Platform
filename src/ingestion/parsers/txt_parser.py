"""
Text Document Parser (supports TXT, Markdown, Log files).
"""
from pathlib import Path
from typing import Optional, List
import logging

from ..base import BaseParser, FileType, DocumentMetadata, ParsedDocument, DocumentSection
from ..normalizer import ContentNormalizer

logger = logging.getLogger(__name__)


class TXTParser(BaseParser):
    """
    Parses plain text, markdown, and log files.
    Robustly attempts multiple common text encodings (UTF-8, UTF-16, Latin-1, CP1252).
    """

    ENCODINGS = ["utf-8", "utf-8-sig", "latin1", "cp1252", "utf-16"]

    @property
    def supported_type(self) -> FileType:
        return FileType.TXT

    def parse(self, file_path: Path, metadata: Optional[DocumentMetadata] = None) -> ParsedDocument:
        if not file_path.exists():
            raise FileNotFoundError(f"TXT file not found: {file_path}")

        file_stat = file_path.stat()
        file_hash = self.calculate_file_hash(file_path)

        if metadata is None:
            metadata = DocumentMetadata(
                filename=file_path.name,
                original_name=file_path.name,
                file_type=FileType.TXT,
                file_size_bytes=file_stat.st_size,
                file_hash=file_hash,
            )
        else:
            metadata.file_size_bytes = file_stat.st_size
            metadata.file_hash = file_hash

        raw_text = ""
        encoding_used = None

        # Attempt multiple encodings
        for enc in self.ENCODINGS:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    raw_text = f.read()
                encoding_used = enc
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if encoding_used is None:
            # Fallback with error replacement
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    raw_text = f.read()
                encoding_used = "utf-8 (lossy)"
            except Exception as e:
                metadata.status = "failed"
                metadata.error_message = f"Failed to decode text file: {str(e)}"
                raise ValueError(f"Could not decode text file {file_path.name}") from e

        metadata.custom_metadata["encoding"] = encoding_used

        # Normalize content
        normalized_text = ContentNormalizer.normalize(raw_text)

        # Break into logical paragraph sections
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        sections: List[DocumentSection] = []

        for idx, para in enumerate(paragraphs):
            norm_para = ContentNormalizer.normalize(para)
            sections.append(
                DocumentSection(
                    section_index=idx,
                    section_title=f"Section {idx + 1}",
                    raw_text=para,
                    normalized_text=norm_para
                )
            )

        metadata.char_count = len(normalized_text)
        metadata.word_count = len(normalized_text.split()) if normalized_text else 0
        metadata.status = "parsed"

        return ParsedDocument(
            metadata=metadata,
            raw_text=raw_text,
            normalized_text=normalized_text,
            sections=sections
        )
