"""
Project Health Scoring Module (Milestone 3 - Requirement 2).

Evaluates overall project health and multi-dimensional operational metrics:
- Overall Project Health Score (0–100)
- Dimension 1: Scope Clarity (0–100)
- Dimension 2: Timeline Risk (0–100)
- Dimension 3: Blocker Count & Issue Severity (0–100)
- Health Status: Healthy, At Risk, or Critical
- Key Risk Drivers & Grounded Recommendations
"""
import time
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from src.architecture.system_design import RetrievedChunk
from src.rag.retriever import SemanticRetriever
from .base import BaseAgent, BaseAgentResult, SourceReference, AgentExecutionStatus
from .scope_agent import ScopeExtractionAgent, ScopeExtractionResult
from .risk_forecast_agent import RiskForecastAgent, RiskForecastResult
from .blocker_action_agent import BlockerActionAgent, BlockerActionResult

logger = logging.getLogger(__name__)


# =====================================================================
# Structured Data Models for Project Health
# =====================================================================

class DimensionScore(BaseModel):
    dimension_name: str
    score: float = Field(..., ge=0.0, le=100.0)
    status: str  # Healthy, At Risk, Critical
    weight: float = 0.33
    summary: str
    key_factors: List[str] = Field(default_factory=list)


class HealthRecommendation(BaseModel):
    priority: str  # High, Medium, Low
    category: str  # Scope, Timeline, Blocker, General
    action: str
    target_owner: str = "Project Leadership"
    grounded_context: Optional[str] = None


class ProjectHealthResult(BaseAgentResult):
    """Full structured output of the Project Health Scoring Module."""
    overall_health_score: float = Field(..., ge=0.0, le=100.0)
    health_status: str  # Healthy, At Risk, Critical
    status_color: str   # green, yellow, red
    scope_clarity_score: float = Field(..., ge=0.0, le=100.0)
    timeline_risk_score: float = Field(..., ge=0.0, le=100.0)
    blocker_score: float = Field(..., ge=0.0, le=100.0)
    dimensions: List[DimensionScore] = Field(default_factory=list)
    key_drivers: List[str] = Field(default_factory=list)
    recommendations: List[HealthRecommendation] = Field(default_factory=list)
    executive_summary: str = ""
    metrics_breakdown: Dict[str, Any] = Field(default_factory=dict)


# =====================================================================
# Project Health Scorer Implementation
# =====================================================================

class ProjectHealthScorer(BaseAgent):
    """
    Synthesizes insights from Scope, Risk, and Blocker agents to compute
    objective, multi-dimensional project health scores grounded in RAG data.
    """

    HEALTH_QUERIES = [
        "project scope goals deliverables milestones status",
        "schedule delay timeline deadline slippage risks",
        "blockers unresolved issues active dependencies blockers",
        "action items meeting notes completion status"
    ]

    def __init__(self, retriever: Optional[SemanticRetriever] = None):
        super().__init__(
            name="Project Health Scoring Module",
            role="health_scorer",
            description="Evaluates project health across Scope Clarity, Timeline Risk, and Blocker Severity dimensions."
        )
        self.retriever = retriever or SemanticRetriever()
        self.scope_agent = ScopeExtractionAgent(retriever=self.retriever)
        self.risk_agent = RiskForecastAgent(retriever=self.retriever)
        self.blocker_agent = BlockerActionAgent(retriever=self.retriever)

    def retrieve_context(self, custom_query: Optional[str] = None, top_k: int = 8) -> List[RetrievedChunk]:
        """Gathers targeted RAG chunks covering scope, risk, and blocker health dimensions."""
        all_chunks: Dict[str, RetrievedChunk] = {}
        queries = [custom_query] if custom_query else self.HEALTH_QUERIES

        for q in queries:
            if not q:
                continue
            chunks = self.retriever.retrieve(query=q, top_k=top_k)
            for c in chunks:
                content_key = c.content.strip().lower()
                if content_key not in all_chunks or c.score > all_chunks[content_key].score:
                    all_chunks[content_key] = c

        sorted_chunks = sorted(all_chunks.values(), key=lambda x: x.score, reverse=True)
        return sorted_chunks[:max(top_k * 4, 30)]

    def compute_health(
        self,
        retrieval_chunks: List[RetrievedChunk],
        scope_res: Optional[ScopeExtractionResult] = None,
        risk_res: Optional[RiskForecastResult] = None,
        blocker_res: Optional[BlockerActionResult] = None
    ) -> ProjectHealthResult:
        """Calculates dimension scores and overall health from multi-agent synthesis."""
        start_time = time.perf_counter()

        # Run subordinate agents if not provided
        if not scope_res:
            scope_res = self.scope_agent.analyze(retrieval_chunks=retrieval_chunks)
        if not risk_res:
            risk_res = self.risk_agent.analyze(retrieval_chunks=retrieval_chunks)
        if not blocker_res:
            blocker_res = self.blocker_agent.analyze(retrieval_chunks=retrieval_chunks)

        grounding_refs = self.map_chunks_to_references(retrieval_chunks)

        # -------------------------------------------------------------
        # 1. Scope Clarity Dimension (0–100)
        # -------------------------------------------------------------
        scope_factors = []
        scope_score = 50.0

        num_goals = len(scope_res.project_goals)
        num_deliverables = len(scope_res.deliverables)
        num_milestones = len(scope_res.milestones)
        has_boundaries = bool(scope_res.scope.in_scope or scope_res.scope.out_of_scope or scope_res.scope.constraints)

        if num_goals > 0:
            scope_score += min(num_goals * 15.0, 25.0)
            scope_factors.append(f"{num_goals} project goal(s) defined")
        else:
            scope_factors.append("No explicit project goals found")

        if num_deliverables > 0:
            scope_score += min(num_deliverables * 4.0, 20.0)
            scope_factors.append(f"{num_deliverables} deliverable(s) extracted")

        if num_milestones > 0:
            scope_score += 10.0
            scope_factors.append(f"{num_milestones} milestone(s) tracked")

        if has_boundaries:
            scope_score += 10.0
            scope_factors.append("Scope boundaries & constraints articulated")

        all_risks = getattr(risk_res, "detected_risks", None) or getattr(risk_res, "identified_risks", [])

        # Penalize for missing information risks
        missing_info_risks = [
            r for r in all_risks 
            if "missing" in getattr(r, "category", "").lower() or "spec" in getattr(r, "category", "").lower()
        ]
        if missing_info_risks:
            scope_score -= len(missing_info_risks) * 10.0
            scope_factors.append(f"{len(missing_info_risks)} specification/information gap(s) identified")

        scope_score = max(10.0, min(100.0, round(scope_score, 1)))
        scope_status = "Healthy" if scope_score >= 75 else "At Risk" if scope_score >= 50 else "Critical"

        # -------------------------------------------------------------
        # 2. Timeline Risk Dimension (0–100, where 100 = on track)
        # -------------------------------------------------------------
        timeline_factors = []
        timeline_score = 90.0

        schedule_risks = [
            r for r in all_risks 
            if "schedule" in getattr(r, "category", "").lower() or "delay" in getattr(r, "title", "").lower() or "timeline" in getattr(r, "category", "").lower() or "dependency" in getattr(r, "category", "").lower()
        ]

        critical_risks = [
            r for r in all_risks 
            if str(getattr(r, "level", None) or getattr(r, "severity", "")).upper() in ["CRITICAL", "SEVERITYLEVEL.CRITICAL", "HIGH", "SEVERITYLEVEL.HIGH"]
            and "crit" in str(getattr(r, "level", None) or getattr(r, "severity", "")).lower()
        ]
        high_risks = [
            r for r in all_risks 
            if str(getattr(r, "level", None) or getattr(r, "severity", "")).upper() in ["HIGH", "SEVERITYLEVEL.HIGH"]
        ]
        medium_risks = [
            r for r in all_risks 
            if str(getattr(r, "level", None) or getattr(r, "severity", "")).upper() in ["MEDIUM", "SEVERITYLEVEL.MEDIUM", "MODERATE"]
        ]

        timeline_score -= len(critical_risks) * 20.0
        timeline_score -= len(high_risks) * 12.0
        timeline_score -= len(medium_risks) * 5.0

        if schedule_risks:
            timeline_factors.append(f"{len(schedule_risks)} schedule/dependency risk(s) active")
        else:
            timeline_factors.append("No critical schedule dependencies flagged")

        if len(scope_res.timelines) > 0:
            timeline_score += 5.0
            timeline_factors.append(f"{len(scope_res.timelines)} deadline(s) established")

        timeline_score = max(10.0, min(100.0, round(timeline_score, 1)))
        timeline_status = "Healthy" if timeline_score >= 75 else "At Risk" if timeline_score >= 50 else "Critical"

        # -------------------------------------------------------------
        # 3. Blocker Count & Issue Severity Dimension (0–100, 100 = unblocked)
        # -------------------------------------------------------------
        blocker_factors = []
        blocker_score = 100.0

        num_blockers = len(blocker_res.active_blockers)
        num_actions = len(blocker_res.action_items)
        num_decisions = len(blocker_res.pending_decisions)

        if num_blockers > 0:
            blocker_score -= num_blockers * 18.0
            blocker_factors.append(f"{num_blockers} active blocker(s) impeding progress")
        else:
            blocker_factors.append("Zero active blocking items identified")

        if num_decisions > 0:
            blocker_score -= num_decisions * 6.0
            blocker_factors.append(f"{num_decisions} pending decision(s) awaiting resolution")

        if num_actions > 0:
            blocker_factors.append(f"{num_actions} action item(s) actively assigned")

        blocker_score = max(10.0, min(100.0, round(blocker_score, 1)))
        blocker_status = "Healthy" if blocker_score >= 75 else "At Risk" if blocker_score >= 50 else "Critical"

        # -------------------------------------------------------------
        # 4. Overall Weighted Health Score & Status
        # -------------------------------------------------------------
        # Weights: 35% Scope Clarity, 35% Blocker Score, 30% Timeline Score
        overall_score = round(
            (0.35 * scope_score) + (0.35 * blocker_score) + (0.30 * timeline_score),
            1
        )
        overall_score = max(10.0, min(100.0, overall_score))

        if overall_score >= 75.0:
            overall_status = "Healthy"
            status_color = "#10b981"  # Emerald Green
        elif overall_score >= 50.0:
            overall_status = "At Risk"
            status_color = "#f59e0b"  # Amber
        else:
            overall_status = "Critical"
            status_color = "#ef4444"  # Red

        # Compile Dimensions
        dimensions = [
            DimensionScore(
                dimension_name="Scope Clarity",
                score=scope_score,
                status=scope_status,
                weight=0.35,
                summary=f"Clarity index: {scope_score}/100. Evaluates definition of project goals, deliverables, and requirements.",
                key_factors=scope_factors
            ),
            DimensionScore(
                dimension_name="Timeline Risk",
                score=timeline_score,
                status=timeline_status,
                weight=0.30,
                summary=f"Schedule confidence: {timeline_score}/100. Evaluates deadline slippage, vendor delays, and schedule feasibility.",
                key_factors=timeline_factors
            ),
            DimensionScore(
                dimension_name="Blocker & Issue Severity",
                score=blocker_score,
                status=blocker_status,
                weight=0.35,
                summary=f"Blocker index: {blocker_score}/100. Evaluates active impediments, unresolved dependencies, and pending decisions.",
                key_factors=blocker_factors
            )
        ]

        # Key Drivers
        key_drivers = []
        if num_blockers > 0:
            key_drivers.append(f"Impediment: {num_blockers} active blocker(s) require escalation.")
        if len(critical_risks) + len(high_risks) > 0:
            key_drivers.append(f"Vulnerability: {len(critical_risks) + len(high_risks)} high/critical risk(s) active in risk register.")
        if num_decisions > 0:
            key_drivers.append(f"Governance: {num_decisions} pending architectural/product decision(s).")
        if num_goals > 0 and num_deliverables > 0:
            key_drivers.append(f"Strength: {num_goals} goals and {num_deliverables} deliverables clearly mapped.")

        # Actionable Recommendations
        recommendations: List[HealthRecommendation] = []
        for b in blocker_res.active_blockers[:3]:
            recommendations.append(
                HealthRecommendation(
                    priority="High",
                    category="Blocker",
                    action=f"Unblock: {b.description}",
                    target_owner=b.owner if b.owner and b.owner != "Unassigned" else "Team Lead",
                    grounded_context=f"Category: {b.category} ({b.source_document})"
                )
            )

        for r in all_risks[:2]:
            mitigation = getattr(r, "suggested_mitigation", None) or getattr(r, "mitigation_recommendation", None)
            if mitigation:
                sev_val = str(getattr(r, "level", None) or getattr(r, "severity", "")).upper()
                recommendations.append(
                    HealthRecommendation(
                        priority="High" if any(s in sev_val for s in ["HIGH", "CRITICAL"]) else "Medium",
                        category="Timeline" if "schedule" in getattr(r, "category", "").lower() else "Risk",
                        action=f"Mitigate '{r.title}': {mitigation}",
                        target_owner="Risk Owner",
                        grounded_context=getattr(r, "source_document", "Uploaded Documentation")
                    )
                )

        if not recommendations:
            recommendations.append(
                HealthRecommendation(
                    priority="Low",
                    category="General",
                    action="Maintain regular sprint cadence and update project artifacts weekly.",
                    target_owner="Project Leadership",
                    grounded_context="RAG Knowledge Base"
                )
            )

        exec_summary = (
            f"Overall Project Health is rated at {overall_score}/100 ({overall_status}). "
            f"Scope Clarity stands at {scope_score}/100 ({scope_status}), "
            f"Timeline Feasibility at {timeline_score}/100 ({timeline_status}), and "
            f"Blocker Severity at {blocker_score}/100 ({blocker_status}) across "
            f"{len(retrieval_chunks)} analyzed knowledge chunks."
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ProjectHealthResult(
            agent_name=self.name,
            agent_role=self.role,
            execution_status=AgentExecutionStatus.SUCCESS,
            retrieved_chunks_count=len(retrieval_chunks),
            grounding_references=grounding_refs,
            overall_health_score=overall_score,
            health_status=overall_status,
            status_color=status_color,
            scope_clarity_score=scope_score,
            timeline_risk_score=timeline_score,
            blocker_score=blocker_score,
            dimensions=dimensions,
            key_drivers=key_drivers,
            recommendations=recommendations,
            executive_summary=exec_summary,
            metrics_breakdown={
                "goals_count": num_goals,
                "deliverables_count": num_deliverables,
                "milestones_count": num_milestones,
                "active_blockers_count": num_blockers,
                "action_items_count": num_actions,
                "pending_decisions_count": num_decisions,
                "critical_risks_count": len(critical_risks),
                "high_risks_count": len(high_risks)
            },
            execution_time_ms=elapsed_ms
        )

    def analyze(
        self,
        retrieval_chunks: Optional[List[RetrievedChunk]] = None,
        query_context: Optional[str] = None
    ) -> ProjectHealthResult:
        """Executes full health calculation workflow."""
        start_time = time.perf_counter()

        if retrieval_chunks is None:
            retrieval_chunks = self.retrieve_context(custom_query=query_context)

        if not retrieval_chunks:
            return ProjectHealthResult(
                agent_name=self.name,
                agent_role=self.role,
                execution_status=AgentExecutionStatus.NO_DATA,
                overall_health_score=50.0,
                health_status="At Risk",
                status_color="#f59e0b",
                scope_clarity_score=50.0,
                timeline_risk_score=50.0,
                blocker_score=50.0,
                notes="No relevant document chunks found in vector database to compute health scores.",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        return self.compute_health(retrieval_chunks=retrieval_chunks)
