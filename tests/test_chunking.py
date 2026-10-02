"""
Unit tests for text chunking and metadata preservation.
"""
import pytest
from src.ingestion.base import ParsedDocument, DocumentMetadata, DocumentSection, FileType
from src.rag.chunking import TextChunker, TextChunk


class TestTextChunker:
    def test_chunk_creation_and_bounds(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20, min_chunk_length=15)
        
        sample_text = (
            "Sprint Risk Report: Authentication module is blocked due to third party API latency. "
            "Database migration scripts require peer review before production deployment. "
            "Frontend team completed dashboard redesign ahead of schedule."
        )

        section = DocumentSection(
            section_index=0,
            section_title="Risks",
            raw_text=sample_text,
            normalized_text=sample_text
        )

        chunks = chunker.chunk_section(
            section=section,
            document_id="doc-123",
            filename="report.txt",
            file_type="txt",
            starting_chunk_index=0
        )

        assert len(chunks) >= 2
        for idx, chunk in enumerate(chunks):
            assert isinstance(chunk, TextChunk)
            assert chunk.document_id == "doc-123"
            assert chunk.chunk_index == idx
            assert chunk.char_count == len(chunk.content)
            assert chunk.token_estimate > 0
            assert chunk.section_title == "Risks"

    def test_invalid_overlap_raises_error(self):
        with pytest.raises(ValueError):
            TextChunker(chunk_size=100, chunk_overlap=120)

    def test_chunk_document(self, sample_txt_file):
        from src.ingestion.parsers import TXTParser
        parser = TXTParser()
        parsed_doc = parser.parse(sample_txt_file)

        chunker = TextChunker(chunk_size=150, chunk_overlap=30)
        chunks = chunker.chunk_document(parsed_doc)

        assert len(chunks) >= 1
        assert parsed_doc.metadata.chunk_count == len(chunks)
        assert chunks[0].filename == sample_txt_file.name
