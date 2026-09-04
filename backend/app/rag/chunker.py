from typing import List
from app.schemas import Chunk, DocumentMetadata
from app.config import settings

class RecursiveCharacterChunker:
    """
    Splits text recursively using section headers, double newlines, single newlines, sentences, and words.
    Ensures optimal chunk size and overlap for vector embeddings.
    """
    def __init__(self, chunk_size: int = settings.CHUNK_SIZE, chunk_overlap: int = settings.CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n---\n", "\n\n", "\n", ". ", " ", ""]

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursive helper to split text into chunks smaller than chunk_size."""
        final_chunks = []
        if not text:
            return final_chunks
            
        separator = separators[-1]
        for s in separators:
            if s == "" or s in text:
                separator = s
                break

        if separator != "":
            splits = text.split(separator)
        else:
            splits = list(text)

        good_splits = []
        for s in splits:
            if good_splits and len(separator.join(good_splits + [s])) > self.chunk_size:
                merged = separator.join(good_splits)
                if len(merged) > self.chunk_size and len(separators) > 1:
                    # Recurse with finer separators
                    next_separators = separators[separators.index(separator) + 1:]
                    final_chunks.extend(self._split_text(merged, next_separators))
                else:
                    final_chunks.append(merged)
                good_splits = [s]
            else:
                good_splits.append(s)

        if good_splits:
            merged = separator.join(good_splits)
            if len(merged) > self.chunk_size and len(separators) > 1:
                next_separators = separators[separators.index(separator) + 1:]
                final_chunks.extend(self._split_text(merged, next_separators))
            else:
                final_chunks.append(merged)

        return final_chunks

    def chunk_document(self, text: str, metadata: DocumentMetadata) -> List[Chunk]:
        """
        Chunks text and builds Chunk schema instances with overlap and character position indices.
        """
        raw_chunks = self._split_text(text, self.separators)
        
        # Merge small chunks with overlap
        chunks: List[Chunk] = []
        current_pos = 0
        
        for idx, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
                
            start_char = text.find(chunk_text, current_pos)
            if start_char == -1:
                start_char = current_pos
            end_char = start_char + len(chunk_text)
            current_pos = max(0, end_char - self.chunk_overlap)
            
            chunk_id = f"{metadata.doc_id}_chk_{idx + 1}"
            
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=metadata.doc_id,
                    filename=metadata.filename,
                    file_type=metadata.file_type,
                    chunk_index=idx + 1,
                    text=chunk_text,
                    char_length=len(chunk_text),
                    start_char=start_char,
                    end_char=end_char
                )
            )
            
        return chunks

chunker = RecursiveCharacterChunker()
