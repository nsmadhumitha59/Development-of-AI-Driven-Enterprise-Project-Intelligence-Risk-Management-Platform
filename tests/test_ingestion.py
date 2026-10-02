"""
Unit and integration tests for Document Ingestion (PDF, DOCX, CSV, TXT).
"""
import pytest
from pathlib import Path
from src.ingestion.base import FileType
from src.ingestion.normalizer import ContentNormalizer
from src.ingestion.parsers import PDFParser, DOCXParser, CSVParser, TXTParser
from src.ingestion.manager import IngestionManager


class TestContentNormalizer:
    def test_normalize_whitespace_and_unicode(self):
        dirty_text = "Project   \t   Intelligence \u200B\u00A0\n\n\n\nNext line   with  spaces."
        normalized = ContentNormalizer.normalize(dirty_text)
        assert "Project Intelligence" in normalized
        assert "\n\n" in normalized
        assert "\n\n\n" not in normalized

    def test_normalize_empty_and_none(self):
        assert ContentNormalizer.normalize(None) == ""
        assert ContentNormalizer.normalize("   ") == ""


class TestTXTParser:
    def test_txt_parsing(self, sample_txt_file):
        parser = TXTParser()
        parsed = parser.parse(sample_txt_file)

        assert parsed.metadata.file_type == FileType.TXT
        assert "AI Project Intelligence" in parsed.normalized_text
        assert parsed.metadata.char_count > 50
        assert len(parsed.sections) >= 1
        assert parsed.metadata.status == "parsed"


class TestCSVParser:
    def test_csv_parsing(self, sample_csv_file):
        parser = CSVParser()
        parsed = parser.parse(sample_csv_file)

        assert parsed.metadata.file_type == FileType.CSV
        assert parsed.metadata.row_count == 4
        assert "Task_ID" in parsed.normalized_text
        assert "TASK-101" in parsed.normalized_text
        assert "Alice Smith" in parsed.normalized_text
        assert len(parsed.sections) == 5  # 1 summary + 4 rows
        assert parsed.metadata.status == "parsed"


class TestDOCXParser:
    def test_docx_parsing(self, sample_docx_file):
        parser = DOCXParser()
        parsed = parser.parse(sample_docx_file)

        assert parsed.metadata.file_type == FileType.DOCX
        assert "Project Charter & Scope" in parsed.normalized_text
        assert "Milestone 1 Ingestion" in parsed.normalized_text
        assert parsed.metadata.char_count > 100
        assert len(parsed.sections) >= 3
        assert parsed.metadata.status == "parsed"


class TestPDFParser:
    def test_pdf_parsing(self, sample_pdf_file):
        parser = PDFParser()
        parsed = parser.parse(sample_pdf_file)

        assert parsed.metadata.file_type == FileType.PDF
        assert parsed.metadata.page_count == 1
        assert "AI Project Intelligence" in parsed.normalized_text
        assert parsed.metadata.char_count > 20
        assert len(parsed.sections) == 1
        assert parsed.metadata.status == "parsed"


class TestIngestionManager:
    def test_batch_ingestion_and_registry(self, ingestion_manager, sample_txt_file, sample_csv_file, sample_docx_file):
        batch = [
            (sample_txt_file, sample_txt_file.name),
            (sample_csv_file, sample_csv_file.name),
            (sample_docx_file, sample_docx_file.name)
        ]
        successful, errors = ingestion_manager.process_batch(batch)

        assert len(errors) == 0
        assert len(successful) == 3

        # Verify docs in registry
        docs = ingestion_manager.list_documents()
        assert len(docs) == 3

        # Verify get document
        doc1_id = successful[0].metadata.document_id
        fetched_meta = ingestion_manager.get_document(doc1_id)
        assert fetched_meta is not None
        assert fetched_meta.filename == successful[0].metadata.filename

        # Verify delete
        deleted = ingestion_manager.delete_document(doc1_id)
        assert deleted is True
        assert ingestion_manager.get_document(doc1_id) is None
        assert len(ingestion_manager.list_documents()) == 2
