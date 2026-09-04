from pathlib import Path
from fastapi.testclient import TestClient

def test_health_endpoint(test_client: TestClient):
    response = test_client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_architecture_endpoint(test_client: TestClient):
    response = test_client.get("/api/v1/system/architecture")
    assert response.status_code == 200
    data = response.json()
    assert "rag_pipeline" in data
    assert "multi_agent_framework" in data
    assert len(data["multi_agent_framework"]) >= 5

def test_upload_and_search_workflow(test_client: TestClient, sample_data_dir: Path):
    # Upload TXT and CSV sample files
    txt_path = sample_data_dir / "project_meeting_notes.txt"
    csv_path = sample_data_dir / "sprint_velocity_metrics.csv"

    with open(txt_path, "rb") as f1, open(csv_path, "rb") as f2:
        files = [
            ("files", ("project_meeting_notes.txt", f1, "text/plain")),
            ("files", ("sprint_velocity_metrics.csv", f2, "text/csv"))
        ]
        upload_res = test_client.post("/api/v1/documents/upload", files=files)

    assert upload_res.status_code == 200
    res_data = upload_res.json()
    assert res_data["success"] is True
    assert res_data["total_uploaded"] == 2
    assert len(res_data["documents"]) == 2

    # Verify document listing
    list_res = test_client.get("/api/v1/documents")
    assert list_res.status_code == 200
    docs = list_res.json()
    assert len(docs) >= 2

    # Perform semantic search query
    search_payload = {
        "query": "What caused the sprint velocity drop?",
        "top_k": 3
    }
    search_res = test_client.post("/api/v1/rag/search", json=search_payload)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_hits"] > 0
    assert len(search_data["hits"]) <= 3

    # Clean up uploaded docs
    for doc in res_data["documents"]:
        del_res = test_client.delete(f"/api/v1/documents/{doc['doc_id']}")
        assert del_res.status_code == 200
