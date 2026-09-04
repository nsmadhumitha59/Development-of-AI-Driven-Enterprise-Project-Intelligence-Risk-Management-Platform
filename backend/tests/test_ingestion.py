import pytest
from pathlib import Path
from app.ingestion.extractors import extract_content, extract_text_from_pdf, extract_text_from_docx, extract_text_from_csv, extract_text_from_txt
from app.ingestion.normalizer import normalize_text
from app.ingestion.metadata import generate_doc_metadata

def test_extract_txt(sample_data_dir: Path):
    txt_path = sample_data_dir / "project_meeting_notes.txt"
    with open(txt_path, "rb") as f:
        content_bytes = f.read()
    text, meta = extract_text_from_txt(content_bytes)
    assert "Sprint 14 Meeting Notes" in text
    assert "API Gateway latency" in text
    assert meta["line_count"] > 0

def test_extract_csv(sample_data_dir: Path):
    csv_path = sample_data_dir / "sprint_velocity_metrics.csv"
    with open(csv_path, "rb") as f:
        content_bytes = f.read()
    text, meta = extract_text_from_csv(content_bytes)
    assert "Planned_Points" in text
    assert "Sprint 14" in text
    assert meta["row_count"] == 4

def test_extract_docx(sample_data_dir: Path):
    docx_path = sample_data_dir / "architecture_requirements.docx"
    with open(docx_path, "rb") as f:
        content_bytes = f.read()
    text, meta = extract_text_from_docx(content_bytes)
    assert "AI Risk Advisor Architecture Requirements" in text
    assert "ChromaDB" in text
    assert meta["paragraph_count"] > 0

def test_extract_pdf(sample_data_dir: Path):
    pdf_path = sample_data_dir / "project_status_report.pdf"
    with open(pdf_path, "rb") as f:
        content_bytes = f.read()
    text, meta = extract_text_from_pdf(content_bytes)
    assert "Quarterly Project Risk" in text
    assert meta["num_pages"] >= 1

def test_normalize_text():
    raw_text = "  Project   Alpha \r\n\n\n\n  Status:  Delayed  \xa0 \n\n"
    normalized = normalize_text(raw_text)
    assert "Project Alpha" in normalized
    assert "Status: Delayed" in normalized
    assert "\r" not in normalized
    assert "\xa0" not in normalized
    assert "\n\n\n" not in normalized

def test_generate_doc_metadata():
    sample_text = "Normalized content of test document for metadata validation."
    sample_bytes = sample_text.encode('utf-8')
    meta = generate_doc_metadata("test_doc.txt", "txt", sample_bytes, sample_text)
    
    assert meta.doc_id.startswith("doc_")
    assert meta.filename == "test_doc.txt"
    assert meta.file_type == "txt"
    assert meta.file_size_bytes == len(sample_bytes)
    assert meta.char_count == len(sample_text)
    assert meta.word_count == len(sample_text.split())
    assert meta.checksum_sha256 is not None

def test_unsupported_file_format():
    with pytest.raises(ValueError, match="Unsupported file format"):
        extract_content(b"dummy data", "unsupported_file.xyz")
