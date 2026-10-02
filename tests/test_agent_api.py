"""
Integration tests for Milestone 2 agent REST API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.app import app
from src.ingestion.parsers import TXTParser
from src.rag.retriever import SemanticRetriever


@pytest.fixture
def client():
    return TestClient(app)


class TestAgentAPIEndpoints:
    def test_scope_agent_endpoint(self, client, sample_txt_file):
        # Ingest document via API
        with open(sample_txt_file, "rb") as f:
            client.post("/api/v1/documents/upload", files=[("files", (sample_txt_file.name, f, "text/plain"))])

        # Call Scope Agent endpoint
        response = client.post("/api/v1/agents/scope", json={"query_context": "project goals deliverables"})
        assert response.status_code == 200
        data = response.json()
        assert data["agent_role"] == "scope_extractor"
        assert "goals" in data
        assert "deliverables" in data

    def test_risk_forecast_endpoint(self, client):
        response = client.post("/api/v1/agents/risk-forecast", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["agent_role"] == "risk_forecaster"
        assert "forecast" in data
        assert "detected_risks" in data

    def test_blockers_actions_endpoint(self, client):
        response = client.post("/api/v1/agents/blockers-actions", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["agent_role"] == "blocker_action_extractor"
        assert "blockers" in data
        assert "action_items" in data

    def test_analyze_all_endpoint(self, client):
        response = client.post("/api/v1/agents/analyze-all", json={"query_context": "milestone status"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "scope_analysis" in data
        assert "risk_and_forecast" in data
        assert "blockers_and_actions" in data
        assert "overall_executive_summary" in data
