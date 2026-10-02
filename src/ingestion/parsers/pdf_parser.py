"""
PDF Document Parser using pypdf.
"""
from pathlib import Path
from typing import Optional, List
import logging
from pypdf import PdfReader

from ..base import BaseParser, FileType, DocumentMetadata, ParsedDocument, DocumentSection
from ..normalizer import ContentNormalizer

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """Extracts text content and page-level metadata from PDF files."""

    @property
    def supported_type(self) -> FileType:
        return FileType.PDF

    def parse(self, file_path: Path, metadata: Optional[DocumentMetadata] = None) -> ParsedDocument:
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        file_stat = file_path.stat()
        file_hash = self.calculate_file_hash(file_path)

        if metadata is None:
            metadata = DocumentMetadata(
                filename=file_path.name,
                original_name=file_path.name,
                file_type=FileType.PDF,
                file_size_bytes=file_stat.st_size,
                file_hash=file_hash,
            )
        else:
            metadata.file_size_bytes = file_stat.st_size
            metadata.file_hash = file_hash

        sections: List[DocumentSection] = []
        raw_pages: List[str] = []
        normalized_pages: List[str] = []

        try:
            reader = PdfReader(str(file_path))
            
            # Extract PDF document info if available
            doc_info = reader.metadata or {}
            custom_meta = {}
            if doc_info.title:
                custom_meta["title"] = str(doc_info.title)
            if doc_info.author:
                custom_meta["author"] = str(doc_info.author)
            if doc_info.subject:
                custom_meta["subject"] = str(doc_info.subject)
            metadata.custom_metadata.update(custom_meta)

            total_pages = len(reader.pages)
            metadata.page_count = total_pages

            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                try:
                    page_text = page.extract_text() or ""
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num} of {file_path.name}: {e}")
                    page_text = ""

                norm_text = ContentNormalizer.normalize(page_text)
                
                raw_pages.append(page_text)
                normalized_pages.append(norm_text)

                sections.append(
                    DocumentSection(
                        section_index=page_idx,
                        section_title=f"Page {page_num}",
                        page_number=page_num,
                        raw_text=page_text,
                        normalized_text=norm_text
                    )
                )

            full_raw_text = "\n\n".join(raw_pages)
            full_norm_text = "\n\n".join([p for p in normalized_pages if p])

            metadata.char_count = len(full_norm_text)
            metadata.word_count = len(full_norm_text.split()) if full_norm_text else 0
            metadata.status = "parsed"

            return ParsedDocument(
                metadata=metadata,
                raw_text=full_raw_text,
                normalized_text=full_norm_text,
                sections=sections
            )

        except Exception as e:
            metadata.status = "failed"
            metadata.error_message = f"Failed to parse PDF: {str(e)}"
            logger.error(f"Failed to parse PDF {file_path}: {e}", exc_info=True)
            raise ValueError(f"Error parsing PDF file {file_path.name}: {str(e)}") from e
