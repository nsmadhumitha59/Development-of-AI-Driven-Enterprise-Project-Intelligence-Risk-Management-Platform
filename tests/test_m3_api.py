"""
Tests for Milestone 3 API Endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.app import app
from src.rag.retriever import SemanticRetriever
from src.ingestion.parsers.docx_parser import DOCXParser
from src.ingestion.parsers.csv_parser import CSVParser
from src.ingestion.parsers.txt_parser import TXTParser


@pytest.fixture
def test_client(
    test_vector_store,
    embedding_service,
    sample_docx_file,
    sample_csv_file,
    sample_txt_file
):
    test_vector_store.reset()
    retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)

    doc_docx = DOCXParser().parse(sample_docx_file)
    doc_csv = CSVParser().parse(sample_csv_file)
    doc_txt = TXTParser().parse(sample_txt_file)

    retriever.index_document(doc_docx)
    retriever.index_document(doc_csv)
    retriever.index_document(doc_txt)

    client = TestClient(app)
    return client


class TestMilestone3APIEndpoints:

    def test_user_stories_endpoint(self, test_client):
        response = test_client.post("/api/v1/m3/docs/user-stories", json={})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_risk_register_endpoint(self, test_client):
        response = test_client.post("/api/v1/m3/docs/risk-register", json={})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_action_items_endpoint(self, test_client):
        response = test_client.post("/api/v1/m3/docs/action-items", json={})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_all_docs_endpoint(self, test_client):
        response = test_client.post("/api/v1/m3/docs/all", json={})
        assert response.status_code == 200
        data = response.json()
        assert "user_stories" in data
        assert "risk_register" in data
        assert "action_items" in data
        assert "markdown_export" in data
        assert "# 📋 AI Project Intelligence" in data["markdown_export"]

    def test_health_score_endpoint(self, test_client):
        response = test_client.post("/api/v1/m3/health-score", json={})
        assert response.status_code == 200
        data = response.json()
        assert "overall_health_score" in data
        assert "health_status" in data
        assert "dimensions" in data
        assert len(data["dimensions"]) == 3
        assert 0.0 <= data["overall_health_score"] <= 100.0

    def test_chat_endpoint(self, test_client):
        response = test_client.post("/api/v1/m3/chat", json={"message": "What are our biggest risks?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "source_references" in data
        assert "suggested_followups" in data
