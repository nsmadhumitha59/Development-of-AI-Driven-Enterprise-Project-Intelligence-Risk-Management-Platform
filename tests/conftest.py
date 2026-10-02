"""
Pytest configuration and synthetic document fixtures for PDF, DOCX, CSV, and TXT testing.
"""
import os
import shutil
import tempfile
from pathlib import Path
import pytest
import pandas as pd
from docx import Document
from pypdf import PdfWriter

from configs.settings import Settings
from src.ingestion.manager import IngestionManager
from src.rag.chunking import TextChunker
from src.rag.embeddings import EmbeddingService
from src.rag.vectorstore import ChromaVectorStore
from src.rag.retriever import SemanticRetriever


@pytest.fixture(scope="session")
def temp_test_dir():
    """Creates an isolated temporary directory for test artifacts and vector databases."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_ai_intelligence_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_settings(temp_test_dir):
    """Configures isolated test settings."""
    test_data = temp_test_dir / "data"
    test_uploads = test_data / "uploads"
    test_processed = test_data / "processed"
    test_vdb = test_data / "vectorstore"
    test_registry = test_data / "registry.json"

    for p in [test_uploads, test_processed, test_vdb]:
        p.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        DATA_DIR=test_data,
        UPLOADS_DIR=test_uploads,
        PROCESSED_DIR=test_processed,
        VECTOR_DB_DIR=test_vdb,
        DOCUMENTS_REGISTRY_FILE=test_registry,
        VECTOR_COLLECTION_NAME="test_collection"
    )
    return settings


@pytest.fixture
def sample_txt_file(temp_test_dir) -> Path:
    """Generates a sample TXT project artifact."""
    file_path = temp_test_dir / "project_architecture_notes.txt"
    content = (
        "AI Project Intelligence Architecture Overview\n\n"
        "The system uses a multi-agent structure to provide automated risk detection, "
        "delivery forecasting, and blocker analysis for software engineering initiatives.\n\n"
        "Milestone 1 focuses on document ingestion, content normalization, sentence-transformers "
        "embedding generation, and ChromaDB vector indexing."
    )
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_csv_file(temp_test_dir) -> Path:
    """Generates a sample CSV project sprint task dataset."""
    file_path = temp_test_dir / "sprint_tasks.csv"
    data = {
        "Task_ID": ["TASK-101", "TASK-102", "TASK-103", "TASK-104"],
        "Title": [
            "Implement Document Ingestion Parser",
            "Setup ChromaDB Local Vector Store",
            "Optimize SentenceTransformers Embeddings",
            "Build FastAPI Endpoints for RAG"
        ],
        "Assignee": ["Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince"],
        "Status": ["Completed", "In Progress", "Completed", "In Review"],
        "Priority": ["High", "Critical", "Medium", "High"]
    }
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    return file_path


@pytest.fixture
def sample_docx_file(temp_test_dir) -> Path:
    """Generates a sample DOCX project document."""
    file_path = temp_test_dir / "project_charter.docx"
    doc = Document()
    doc.add_heading("Project Charter & Scope", level=0)
    
    doc.add_heading("Project Objectives", level=1)
    doc.add_paragraph(
        "The AI Project Intelligence system aims to minimize sprint slippage and provide "
        "predictive risk advisory to engineering leaders and scrum masters."
    )

    doc.add_heading("Key Deliverables", level=1)
    doc.add_paragraph(
        "Deliverables include automated ingestion of PDF and DOCX specifications, vector storage, "
        "and real-time semantic query retrieval."
    )

    table = doc.add_table(rows=1, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Phase"
    hdr_cells[1].text = "Target Date"
    hdr_cells[2].text = "Status"

    row_cells = table.add_row().cells
    row_cells[0].text = "Milestone 1 Ingestion"
    row_cells[1].text = "2026-Q4"
    row_cells[2].text = "Active"

    doc.save(str(file_path))
    return file_path


@pytest.fixture
def sample_pdf_file(temp_test_dir) -> Path:
    """Generates a valid sample PDF document with extracted text."""
    file_path = temp_test_dir / "system_specification.pdf"
    
    # We can create a simple PDF with pypdf or text stream
    # Note: creating a PDF with text stream in pypdf
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject
    
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    
    # Insert stream with text operator: BT /F1 12 Tf 50 700 Td (AI Project Intelligence Specification) Tj ET
    text_content = (
        b"BT\n"
        b"/Helvetica 12 Tf\n"
        b"50 700 Td\n"
        b"(AI Project Intelligence System Specification) Tj\n"
        b"0 -20 Td\n"
        b"(This PDF document specifies the RAG retrieval pipeline and vector indexing requirements.) Tj\n"
        b"0 -20 Td\n"
        b"(Milestone 1 guarantees accurate extraction for PDF, DOCX, CSV, and TXT files.) Tj\n"
        b"ET\n"
    )
    stream_obj = DecodedStreamObject()
    stream_obj.set_data(text_content)
    page[NameObject("/Contents")] = writer._add_object(stream_obj)
    
    # Add Font resource to page
    font_dict = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    fonts_res = DictionaryObject({
        NameObject("/Helvetica"): writer._add_object(font_dict)
    })
    resources = DictionaryObject({
        NameObject("/Font"): writer._add_object(fonts_res)
    })
    page[NameObject("/Resources")] = writer._add_object(resources)

    with open(file_path, "wb") as f:
        writer.write(f)

    return file_path


@pytest.fixture
def ingestion_manager(test_settings):
    return IngestionManager(
        uploads_dir=test_settings.UPLOADS_DIR,
        processed_dir=test_settings.PROCESSED_DIR,
        registry_file=test_settings.DOCUMENTS_REGISTRY_FILE
    )


@pytest.fixture
def test_vector_store(test_settings):
    return ChromaVectorStore(
        persist_directory=test_settings.VECTOR_DB_DIR,
        collection_name=test_settings.VECTOR_COLLECTION_NAME
    )


@pytest.fixture
def embedding_service():
    return EmbeddingService.get_instance()


@pytest.fixture
def semantic_retriever(test_vector_store, embedding_service):
    return SemanticRetriever(
        vector_store=test_vector_store,
        embedding_service=embedding_service,
        chunker=TextChunker(chunk_size=300, chunk_overlap=50)
    )
