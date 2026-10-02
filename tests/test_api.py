"""
API endpoint tests for FastAPI server.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAPIEndpoints:
    def test_health_check(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["milestone"] == 1
        assert "all-MiniLM-L6-v2" in data["embedding_model"]

    def test_document_upload_and_query_flow(self, client, sample_txt_file):
        # 1. Upload TXT file
        with open(sample_txt_file, "rb") as f:
            files = [("files", (sample_txt_file.name, f, "text/plain"))]
            upload_res = client.post("/api/v1/documents/upload", files=files)

        assert upload_res.status_code == 201
        data = upload_res.json()
        assert data["success"] is True
        assert data["successful_count"] == 1
        doc_id = data["documents"][0]["document_id"]

        # 2. List documents
        list_res = client.get("/api/v1/documents")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert any(d["document_id"] == doc_id for d in list_data["documents"])

        # 3. Get document details
        detail_res = client.get(f"/api/v1/documents/{doc_id}")
        assert detail_res.status_code == 200
        assert "AI Project Intelligence" in detail_res.json()["preview_text"]

        # 4. Query RAG endpoint
        query_payload = {
            "query": "What is the focus of Milestone 1?",
            "top_k": 3
        }
        query_res = client.post("/api/v1/rag/query", json=query_payload)
        assert query_res.status_code == 200
        qdata = query_res.json()
        assert qdata["total_results"] > 0
        assert "Milestone 1" in qdata["results"][0]["content"]

        # 5. Delete document
        del_res = client.delete(f"/api/v1/documents/{doc_id}")
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True
