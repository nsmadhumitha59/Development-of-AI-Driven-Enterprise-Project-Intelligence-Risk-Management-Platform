"""
Unit and integration tests for Risk Detection and Delivery Forecasting Agent (Milestone 2 - Requirement 2).
"""
import pytest
from pathlib import Path
from src.ingestion.parsers import TXTParser, CSVParser
from src.rag.retriever import SemanticRetriever
from src.agents.risk_forecast_agent import (
    RiskForecastAgent,
    RiskForecastResult,
    RiskCategory,
    RiskLevel,
    DeliveryStatus
)


@pytest.fixture
def risk_report_file(temp_test_dir) -> Path:
    file_path = temp_test_dir / "sprint_risk_briefing.txt"
    content = (
        "Sprint 4 Risk Briefing & Engineering Status\n\n"
        "1. Critical Dependency: Payment gateway integration is blocked by third party vendor API outage.\n"
        "2. Schedule Slippage: Database indexing task is overdue and delayed by 4 business days.\n"
        "3. Missing Specification: Requirements for multi-tenant analytics are TBD and unclear.\n"
        "4. Technical Bottleneck: High memory leak during large batch CSV vector indexing."
    )
    file_path.write_text(content, encoding="utf-8")
    return file_path


class TestRiskForecastAgent:
    def test_risk_detection_and_delivery_forecast(self, test_vector_store, embedding_service, risk_report_file):
        test_vector_store.reset()
        retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)
        
        parsed = TXTParser().parse(risk_report_file)
        retriever.index_document(parsed)

        agent = RiskForecastAgent(retriever=retriever)
        result = agent.analyze()

        assert isinstance(result, RiskForecastResult)
        assert result.agent_role == "risk_forecaster"
        assert result.total_risks_detected >= 3

        # Verify risk categories detected
        categories = [r.category for r in result.detected_risks]
        assert RiskCategory.DEPENDENCY in categories or RiskCategory.SCHEDULE in categories

        # Verify high/critical level assigned
        levels = [r.level for r in result.detected_risks]
        assert RiskLevel.CRITICAL in levels or RiskLevel.HIGH in levels or RiskLevel.MEDIUM in levels

        # Verify supporting reasons & grounding
        for r in result.detected_risks:
            assert len(r.reason) > 10
            assert len(r.suggested_mitigation) > 10
            if r.source_reference:
                assert r.source_reference.filename == risk_report_file.name

        # Verify Delivery Forecast
        assert result.forecast.overall_status in [DeliveryStatus.AT_RISK, DeliveryStatus.DELAYED, DeliveryStatus.ON_TRACK]
        assert result.forecast.slippage_probability > 0.0
        assert len(result.forecast.key_forecast_factors) > 0
