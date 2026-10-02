"""
Milestone 2 Multi-Agent Orchestrator Pipeline.

Coordinates:
1. Scope & Deliverable Extraction Agent
2. Risk Detection & Delivery Forecasting Agent
3. Blocker & Action Item Identification Agent
"""
import time
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from src.rag.retriever import SemanticRetriever
from .base import AgentExecutionStatus
from .scope_agent import ScopeExtractionAgent, ScopeExtractionResult
from .risk_forecast_agent import RiskForecastAgent, RiskForecastResult
from .blocker_action_agent import BlockerActionAgent, BlockerActionResult

logger = logging.getLogger(__name__)


class Milestone2AnalysisResult(BaseModel):
    """Unified structured insight report produced by all Milestone 2 agents."""
    success: bool = True
    project_title: str = "AI Project Intelligence"
    timestamp: str
    total_execution_time_ms: float
    scope_analysis: ScopeExtractionResult
    risk_and_forecast: RiskForecastResult
    blockers_and_actions: BlockerActionResult
    overall_executive_summary: str


class Milestone2MultiAgentPipeline:
    """
    Executes the multi-agent pipeline for Milestone 2:
    Uploaded Docs -> RAG Knowledge Base -> RAG Retrieval -> Scope Agent + Risk/Forecast Agent + Blocker/Action Agent -> Structured Insights
    """

    def __init__(self, retriever: Optional[SemanticRetriever] = None):
        self.retriever = retriever or SemanticRetriever()
        self.scope_agent = ScopeExtractionAgent(retriever=self.retriever)
        self.risk_agent = RiskForecastAgent(retriever=self.retriever)
        self.blocker_agent = BlockerActionAgent(retriever=self.retriever)

    def run_all(self, focus_query: Optional[str] = None) -> Milestone2AnalysisResult:
        """Runs all 3 Milestone 2 agents and returns consolidated structured insights."""
        start_time = time.perf_counter()

        # Run all agents
        scope_res = self.scope_agent.analyze(query_context=focus_query)
        risk_res = self.risk_agent.analyze(query_context=focus_query)
        blocker_res = self.blocker_agent.analyze(query_context=focus_query)

        # Unified Executive Summary
        summary_lines = [
            f"Project: {scope_res.project_title or 'Active Workspace'}",
            f"Scope Status: {len(scope_res.goals)} goals, {len(scope_res.deliverables)} deliverables, {len(scope_res.milestones)} milestones identified.",
            f"Delivery & Risk Status: {risk_res.forecast.overall_status.value} (Slippage Probability: {round(risk_res.forecast.slippage_probability * 100, 1)}%) with {risk_res.total_risks_detected} risk items detected.",
            f"Impediment Status: {blocker_res.total_blockers} active blockers, {blocker_res.total_action_items} action items, and {blocker_res.total_pending_decisions} pending decisions."
        ]
        overall_summary = " \n".join(summary_lines)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return Milestone2AnalysisResult(
            success=True,
            project_title=scope_res.project_title or "Project Workspace",
            timestamp=scope_res.timestamp,
            total_execution_time_ms=elapsed_ms,
            scope_analysis=scope_res,
            risk_and_forecast=risk_res,
            blockers_and_actions=blocker_res,
            overall_executive_summary=overall_summary
        )
