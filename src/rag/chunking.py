"""
Text Chunking Module for RAG Pipeline.
Implements recursive, boundary-aware splitting with sliding window overlap and rich metadata tracking.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

from configs.settings import settings
from src.ingestion.base import ParsedDocument, DocumentSection


class TextChunk(BaseModel):
    """Represents a discrete semantic chunk of text with rich indexing metadata."""
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    filename: str
    file_type: str
    chunk_index: int
    content: str
    start_char: int
    end_char: int
    page_number: Optional[int] = None
    row_number: Optional[int] = None
    section_title: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    char_count: int = 0
    token_estimate: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TextChunker:
    """
    Recursive structure-aware text splitter.
    Splits text across hierarchical boundaries (paragraphs -> sentences -> words)
    while maintaining target chunk sizes and sliding window overlap.
    """

    SEPARATORS = ["\n\n", "\n", ". ", "; ", "? ", "! ", " ", ""]

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        min_chunk_length: int = settings.MIN_CHUNK_LENGTH
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError(f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively breaks text using ordered hierarchy of delimiters."""
        final_chunks: List[str] = []
        if not separators:
            # Fallback: hard character slice
            return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep == "":
            splits = list(text)
        else:
            splits = text.split(sep)

        current_piece = []
        current_len = 0

        for split in splits:
            if not split:
                continue

            split_len = len(split) + (len(sep) if current_piece else 0)

            if current_len + split_len <= self.chunk_size:
                current_piece.append(split)
                current_len += split_len
            else:
                if current_piece:
                    joined = sep.join(current_piece).strip()
                    if len(joined) > self.chunk_size and remaining_seps:
                        final_chunks.extend(self._split_text_recursive(joined, remaining_seps))
                    elif joined:
                        final_chunks.append(joined)
                    current_piece = []
                    current_len = 0

                if len(split) > self.chunk_size:
                    if remaining_seps:
                        final_chunks.extend(self._split_text_recursive(split, remaining_seps))
                    else:
                        final_chunks.append(split)
                else:
                    current_piece.append(split)
                    current_len = len(split)

        if current_piece:
            joined = sep.join(current_piece).strip()
            if joined:
                if len(joined) > self.chunk_size and remaining_seps:
                    final_chunks.extend(self._split_text_recursive(joined, remaining_seps))
                else:
                    final_chunks.append(joined)

        return final_chunks

    def _apply_sliding_window(self, splits: List[str]) -> List[str]:
        """Combines short splits and applies overlap sliding window."""
        chunks: List[str] = []
        accumulated: List[str] = []
        accumulated_len = 0

        for split in splits:
            split_clean = split.strip()
            if not split_clean:
                continue

            if accumulated_len + len(split_clean) + 1 <= self.chunk_size:
                accumulated.append(split_clean)
                accumulated_len += len(split_clean) + 1
            else:
                if accumulated:
                    chunk_text = " ".join(accumulated).strip()
                    if len(chunk_text) >= self.min_chunk_length:
                        chunks.append(chunk_text)

                    # Compute overlap from end of accumulated
                    overlap_accum: List[str] = []
                    overlap_len = 0
                    for item in reversed(accumulated):
                        if overlap_len + len(item) + 1 <= self.chunk_overlap:
                            overlap_accum.insert(0, item)
                            overlap_len += len(item) + 1
                        else:
                            break
                    accumulated = overlap_accum
                    accumulated_len = overlap_len

                accumulated.append(split_clean)
                accumulated_len += len(split_clean) + 1

        if accumulated:
            chunk_text = " ".join(accumulated).strip()
            if len(chunk_text) >= self.min_chunk_length:
                chunks.append(chunk_text)

        return chunks

    def chunk_section(
        self,
        section: DocumentSection,
        document_id: str,
        filename: str,
        file_type: str,
        starting_chunk_index: int
    ) -> List[TextChunk]:
        """Chunks a single DocumentSection and returns TextChunk objects."""
        text = section.normalized_text or section.raw_text
        if not text or len(text.strip()) < self.min_chunk_length:
            return []

        # Split and window
        initial_splits = self._split_text_recursive(text, self.SEPARATORS)
        chunk_texts = self._apply_sliding_window(initial_splits)

        chunks: List[TextChunk] = []
        current_char_offset = 0

        for idx, c_text in enumerate(chunk_texts):
            start_pos = text.find(c_text[:30], current_char_offset) if len(c_text) >= 30 else current_char_offset
            if start_pos == -1:
                start_pos = current_char_offset
            end_pos = start_pos + len(c_text)
            current_char_offset = max(start_pos + 1, current_char_offset)

            # Rough token estimate (~4 chars per token)
            tokens = max(1, len(c_text) // 4)

            chunk = TextChunk(
                document_id=document_id,
                filename=filename,
                file_type=file_type,
                chunk_index=starting_chunk_index + idx,
                content=c_text,
                start_char=start_pos,
                end_char=end_pos,
                page_number=section.page_number,
                row_number=section.row_number,
                section_title=section.section_title,
                char_count=len(c_text),
                token_estimate=tokens,
                metadata={
                    "section_index": section.section_index,
                    "section_title": section.section_title or ""
                }
            )
            chunks.append(chunk)

        return chunks

    def chunk_document(self, parsed_doc: ParsedDocument) -> List[TextChunk]:
        """
        Chunks an entire ParsedDocument by traversing its sections.
        Maintains global document chunk indices and metadata.
        """
        all_chunks: List[TextChunk] = []
        meta = parsed_doc.metadata

        if parsed_doc.sections:
            for section in parsed_doc.sections:
                section_chunks = self.chunk_section(
                    section=section,
                    document_id=meta.document_id,
                    filename=meta.original_name,
                    file_type=meta.file_type.value,
                    starting_chunk_index=len(all_chunks)
                )
                all_chunks.extend(section_chunks)
        else:
            # Fallback for document with single text body
            fallback_section = DocumentSection(
                section_index=0,
                section_title="Full Text",
                raw_text=parsed_doc.raw_text,
                normalized_text=parsed_doc.normalized_text
            )
            all_chunks = self.chunk_section(
                section=fallback_section,
                document_id=meta.document_id,
                filename=meta.original_name,
                file_type=meta.file_type.value,
                starting_chunk_index=0
            )

        # Update metadata chunk count
        meta.chunk_count = len(all_chunks)
        return all_chunks
