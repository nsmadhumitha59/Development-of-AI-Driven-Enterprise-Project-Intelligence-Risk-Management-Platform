"""
Risk Detection and Delivery Forecasting Agent (Milestone 2 - Requirement 2).

Identifies:
- Schedule risks
- Dependency gaps
- Missing information
- Delivery challenges
- Potential deadline risks
Assigns risk levels (Low, Medium, High, Critical) with supporting reasons & source references.
Generates a grounded delivery forecast based on extracted timeline signals.
"""
import re
import time
import logging
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

from src.architecture.system_design import RetrievedChunk
from src.rag.retriever import SemanticRetriever
from .base import BaseAgent, BaseAgentResult, SourceReference, AgentExecutionStatus

logger = logging.getLogger(__name__)


class RiskCategory(str, Enum):
    SCHEDULE = "Schedule & Timeline"
    DEPENDENCY = "Dependency & External Blockers"
    MISSING_INFO = "Missing Information & Ambiguity"
    DELIVERY_CHALLENGE = "Delivery & Technical Challenge"
    RESOURCE = "Resource & Staffing"
    QUALITY = "Quality & Regression Risk"
    OPERATIONAL = "Operational & Facility Risk"
    SAFETY = "Safety & Compliance Risk"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class DeliveryStatus(str, Enum):
    ON_TRACK = "On Track"
    AT_RISK = "At Risk"
    DELAYED = "Delayed"
    UNCERTAIN = "Uncertain / Insufficient Data"


class DetectedRisk(BaseModel):
    risk_id: str = Field(default_factory=lambda: f"RSK-{uuid.uuid4().hex[:6].upper()}")
    title: str
    category: RiskCategory
    level: RiskLevel
    reason: str
    impact: str
    suggested_mitigation: str
    source_document: str = "unknown"
    supporting_context: Optional[str] = None
    source_reference: Optional[SourceReference] = None


class MilestoneForecast(BaseModel):
    milestone_name: str
    projected_status: DeliveryStatus
    target_date: Optional[str] = None
    forecast_confidence: float = 0.8  # 0.0 to 1.0
    rationale: str


class DeliveryForecast(BaseModel):
    overall_status: DeliveryStatus = DeliveryStatus.ON_TRACK
    slippage_probability: float = Field(default=0.0, description="Estimated probability of sprint/milestone delay (0.0 - 1.0)")
    confidence_level: str = "Medium"  # High, Medium, Low
    key_forecast_factors: List[str] = Field(default_factory=list)
    milestone_forecasts: List[MilestoneForecast] = Field(default_factory=list)
    delivery_summary: str = ""


class RiskForecastResult(BaseAgentResult):
    """Structured output for Risk Detection & Delivery Forecasting Agent."""
    total_risks_detected: int = 0
    risk_summary_counts: Dict[str, int] = Field(default_factory=dict)
    detected_risks: List[DetectedRisk] = Field(default_factory=list)
    identified_risks: List[DetectedRisk] = Field(default_factory=list)  # Backward/forward alias
    forecast: DeliveryForecast = Field(default_factory=DeliveryForecast)
    delivery_forecast: DeliveryForecast = Field(default_factory=DeliveryForecast)  # Alias
    executive_risk_statement: str = ""


# =====================================================================
# Risk Detection & Delivery Forecasting Agent Implementation
# =====================================================================

class RiskForecastAgent(BaseAgent):
    """
    RAG-driven agent detecting delivery risks, dependency gaps, and timeline slippages.
    Grounded directly in indexed document chunks.
    """

    RISK_QUERIES = [
        "project risks blockers delays dependencies challenges latency failures",
        "potential risks observed risks risk log issues",
        "missing requirements incomplete specifications technical bottlenecks",
        "deadline timeline slippage overdue pending review blocked tickets"
    ]

    def __init__(self, retriever: Optional[SemanticRetriever] = None):
        super().__init__(
            name="Risk Detection & Delivery Forecasting Agent",
            role="risk_forecaster",
            description="Identifies schedule risks, dependency gaps, missing info, and calculates delivery forecasts."
        )
        self.retriever = retriever or SemanticRetriever()

    def retrieve_context(self, custom_query: Optional[str] = None, top_k: int = 8) -> List[RetrievedChunk]:
        """Gathers targeted RAG chunks covering risks, bottlenecks, dependencies, and timelines."""
        all_chunks: Dict[str, RetrievedChunk] = {}
        queries = [custom_query] if custom_query else self.RISK_QUERIES

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

    def analyze(
        self,
        retrieval_chunks: Optional[List[RetrievedChunk]] = None,
        query_context: Optional[str] = None
    ) -> RiskForecastResult:
        """Executes risk analysis and delivery forecasting on retrieved chunks."""
        start_time = time.perf_counter()

        if retrieval_chunks is None:
            retrieval_chunks = self.retrieve_context(custom_query=query_context)

        if not retrieval_chunks:
            return RiskForecastResult(
                agent_name=self.name,
                agent_role=self.role,
                execution_status=AgentExecutionStatus.NO_DATA,
                notes="No project chunks found for risk analysis in knowledge base.",
                executive_risk_statement="No risks identified due to lack of retrieved documents.",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        grounding_refs = self.map_chunks_to_references(retrieval_chunks)

        detected_risks: List[DetectedRisk] = []
        high_risk_signals: int = 0
        medium_risk_signals: int = 0
        low_risk_signals: int = 0

        # Pattern indicators
        schedule_keywords = ["delay", "overdue", "late", "slippage", "behind schedule", "deadline risk", "bottleneck", "loading capacity is limited"]
        dependency_keywords = ["dependency", "blocked by", "waiting on", "waiting for", "third party", "vendor", "external api", "integration", "supplier"]
        missing_info_keywords = ["tbd", "unclear", "missing requirement", "unspecified", "undefined", "needs clarification", "todo"]
        challenge_keywords = ["critical", "failure", "memory leak", "oom", "bug", "vulnerability", "complex", "refactor", "pos downtime", "stock discrepancy"]
        resource_keywords = ["staff", "staffing", "shortage", "unfilled", "volunteer", "capacity"]
        safety_keywords = ["safety", "inspection", "emergency", "exit", "generator test"]

        for chunk in retrieval_chunks:
            text = chunk.content
            filename = chunk.metadata.filename
            ref = SourceReference(
                chunk_id=chunk.chunk_id,
                document_id=chunk.metadata.document_id,
                filename=filename,
                file_type=chunk.metadata.file_type.value if hasattr(chunk.metadata.file_type, 'value') else str(chunk.metadata.file_type),
                page_number=chunk.metadata.page_number,
                row_number=chunk.metadata.row_number,
                section_title=chunk.metadata.section_title,
                similarity_score=chunk.score,
                snippet=chunk.content[:200] + ("..." if len(chunk.content) > 200 else "")
            )

            raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
            current_section = None

            for line in raw_lines:
                lower_line = line.lower()

                # Track risk sections
                if re.match(r"^(?:potential\s+risks?|risks?\s+identified|observed\s+risks?|risk\s+log)[:\s]*$", lower_line):
                    current_section = "risks"
                    continue
                elif re.match(r"^(?:blockers?|action\s+items?|objectives?|goals?)[:\s]*$", lower_line):
                    current_section = None

                is_in_risk_section = (current_section == "risks" and len(line) > 10)
                is_risk_line = is_in_risk_section or any(k in lower_line for k in ["risk:", "risk_id:", "potential risk", "observed risk", "severity:"]) or any(k in lower_line for k in schedule_keywords + dependency_keywords + missing_info_keywords + challenge_keywords)

                if not is_risk_line or len(line) < 8:
                    continue

                clean_line = line
                for prefix in [r"^(?:\d+[\.\)]|\*|-|•)\s*", r"^Row\s+\d+:?\s*"]:
                    clean_line = re.sub(prefix, "", clean_line, flags=re.IGNORECASE).strip()

                if "status: completed" in lower_line or "completed" == lower_line:
                    continue

                # 1. Dependency & External Risks
                if any(k in lower_line for k in dependency_keywords):
                    is_critical = any(c in lower_line for c in ["critical", "fatal", "blocker", "severe", "outage"])
                    r_level = RiskLevel.CRITICAL if is_critical else RiskLevel.HIGH if "blocked" in lower_line else RiskLevel.MEDIUM
                    title = f"Dependency Constraint in {filename}"
                    reason = f"Identified dependency or external integration constraint: '{clean_line[:130]}'"
                    impact = "May stall dependent workstreams and delay component delivery."
                    mitigation = "Establish explicit SLA with upstream partners and implement mocked fallback interfaces."

                    if not any(r.reason == reason for r in detected_risks):
                        detected_risks.append(
                            DetectedRisk(
                                title=title,
                                category=RiskCategory.DEPENDENCY,
                                level=r_level,
                                reason=reason,
                                impact=impact,
                                suggested_mitigation=mitigation,
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )
                        if r_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                            high_risk_signals += 1
                        else:
                            medium_risk_signals += 1

                # 2. Schedule & Timeline Risks
                elif any(k in lower_line for k in schedule_keywords):
                    r_level = RiskLevel.HIGH if ("critical" in lower_line or "severe" in lower_line or "overdue" in lower_line) else RiskLevel.MEDIUM
                    title = f"Schedule Slippage Risk ({filename})"
                    reason = f"Timeline delay signal detected: '{clean_line[:130]}'"
                    impact = "Potential milestone date shift and delivery timeline extension."
                    mitigation = "Re-estimate remaining story points, reallocate engineering capacity, or adjust sprint scope."

                    if not any(r.reason == reason for r in detected_risks):
                        detected_risks.append(
                            DetectedRisk(
                                title=title,
                                category=RiskCategory.SCHEDULE,
                                level=r_level,
                                reason=reason,
                                impact=impact,
                                suggested_mitigation=mitigation,
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )
                        if r_level == RiskLevel.HIGH:
                            high_risk_signals += 1
                        else:
                            medium_risk_signals += 1

                # 3. Missing Information / Ambiguity
                elif any(k in lower_line for k in missing_info_keywords):
                    r_level = RiskLevel.MEDIUM if ("tbd" in lower_line or "unclear" in lower_line) else RiskLevel.LOW
                    title = f"Unspecified Requirement / Information Gap"
                    reason = f"Found ambiguity or missing definition: '{clean_line[:130]}'"
                    impact = "Rework risk during development phase if requirements shift."
                    mitigation = "Conduct clarification session with product owner to finalize specifications."

                    if not any(r.reason == reason for r in detected_risks):
                        detected_risks.append(
                            DetectedRisk(
                                title=title,
                                category=RiskCategory.MISSING_INFO,
                                level=r_level,
                                reason=reason,
                                impact=impact,
                                suggested_mitigation=mitigation,
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )
                        if r_level == RiskLevel.MEDIUM:
                            medium_risk_signals += 1
                        else:
                            low_risk_signals += 1

                # 4. Resource & Staffing Risks
                elif any(k in lower_line for k in resource_keywords):
                    r_level = RiskLevel.HIGH if "shortage" in lower_line or "unfilled" in lower_line else RiskLevel.MEDIUM
                    title = f"Resource & Staffing Risk ({filename})"
                    reason = f"Staffing constraint detected: '{clean_line[:130]}'"
                    impact = "May reduce operational capacity and increase turnaround times."
                    mitigation = "Accelerate hiring pipeline or temporarily reassign cross-functional resources."

                    if not any(r.reason == reason for r in detected_risks):
                        detected_risks.append(
                            DetectedRisk(
                                title=title,
                                category=RiskCategory.RESOURCE,
                                level=r_level,
                                reason=reason,
                                impact=impact,
                                suggested_mitigation=mitigation,
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )
                        if r_level == RiskLevel.HIGH:
                            high_risk_signals += 1
                        else:
                            medium_risk_signals += 1

                # 5. Delivery / Technical Challenges
                elif any(k in lower_line for k in challenge_keywords) and ("status: completed" not in lower_line):
                    r_level = RiskLevel.CRITICAL if "critical" in lower_line or "downtime" in lower_line else RiskLevel.HIGH if "vulnerability" in lower_line or "leak" in lower_line else RiskLevel.MEDIUM
                    title = f"Technical Delivery Challenge"
                    reason = f"Technical risk identified in document: '{clean_line[:130]}'"
                    impact = "Could impact system stability, throughput, or deployment readiness."
                    mitigation = "Conduct technical spike and implement automated regression testing."

                    if not any(r.reason == reason for r in detected_risks):
                        detected_risks.append(
                            DetectedRisk(
                                title=title,
                                category=RiskCategory.DELIVERY_CHALLENGE,
                                level=r_level,
                                reason=reason,
                                impact=impact,
                                suggested_mitigation=mitigation,
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )
                        if r_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                            high_risk_signals += 1
                        else:
                            medium_risk_signals += 1

                # 6. Safety & Operational
                elif is_in_risk_section or any(k in lower_line for k in safety_keywords):
                    r_level = RiskLevel.MEDIUM
                    title = f"Operational Risk ({filename})"
                    reason = f"Operational risk signal detected: '{clean_line[:130]}'"
                    impact = "May affect workflow execution and operational compliance."
                    mitigation = "Execute scheduled maintenance and verify safety protocols."

                    if not any(r.reason == reason for r in detected_risks):
                        detected_risks.append(
                            DetectedRisk(
                                title=title,
                                category=RiskCategory.OPERATIONAL,
                                level=r_level,
                                reason=reason,
                                impact=impact,
                                suggested_mitigation=mitigation,
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )
                        medium_risk_signals += 1

        # Fallback heuristic baseline if documents are clean
        if not detected_risks:
            detected_risks.append(
                DetectedRisk(
                    title="Low Operational Variance Risk",
                    category=RiskCategory.SCHEDULE,
                    level=RiskLevel.LOW,
                    reason="No major blockers or critical delays detected across parsed project artifacts.",
                    impact="Minimal impact on baseline delivery schedule.",
                    suggested_mitigation="Maintain sprint cadence and monitor upcoming milestone handoffs.",
                    source_document=grounding_refs[0].filename if grounding_refs else "unknown",
                    source_reference=grounding_refs[0] if grounding_refs else None
                )
            )
            low_risk_signals += 1

        # Calculate Delivery Forecast grounded in risk counts
        if high_risk_signals > 0:
            overall_status = DeliveryStatus.AT_RISK
            slippage_prob = min(0.85, 0.40 + (high_risk_signals * 0.15))
            confidence = "High"
            summary_statement = f"Delivery is AT RISK due to {high_risk_signals} high-priority schedule/dependency bottlenecks."
        elif medium_risk_signals >= 2:
            overall_status = DeliveryStatus.AT_RISK
            slippage_prob = min(0.55, 0.25 + (medium_risk_signals * 0.08))
            confidence = "Medium"
            summary_statement = f"Delivery is slightly AT RISK with {medium_risk_signals} moderate risk factors."
        else:
            overall_status = DeliveryStatus.ON_TRACK
            slippage_prob = 0.10
            confidence = "High"
            summary_statement = "Delivery is currently ON TRACK with low risk profile."

        forecast_factors = [
            f"Detected {len(detected_risks)} total risk items ({high_risk_signals} High/Critical, {medium_risk_signals} Medium, {low_risk_signals} Low)",
            f"Knowledge grounding over {len(retrieval_chunks)} chunks across uploaded project artifacts",
            f"Estimated timeline slippage probability: {round(slippage_prob * 100, 1)}%"
        ]

        # Milestone specific forecast projection
        milestone_projections: List[MilestoneForecast] = [
            MilestoneForecast(
                milestone_name="Active Project Milestone",
                projected_status=overall_status,
                target_date="Target End Date",
                forecast_confidence=0.85,
                rationale=summary_statement
            )
        ]

        delivery_forecast = DeliveryForecast(
            overall_status=overall_status,
            slippage_probability=round(slippage_prob, 3),
            confidence_level=confidence,
            key_forecast_factors=forecast_factors,
            milestone_forecasts=milestone_projections,
            delivery_summary=summary_statement
        )

        counts_dict = {
            "critical": sum(1 for r in detected_risks if r.level == RiskLevel.CRITICAL),
            "high": sum(1 for r in detected_risks if r.level == RiskLevel.HIGH),
            "medium": sum(1 for r in detected_risks if r.level == RiskLevel.MEDIUM),
            "low": sum(1 for r in detected_risks if r.level == RiskLevel.LOW)
        }

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return RiskForecastResult(
            agent_name=self.name,
            agent_role=self.role,
            execution_status=AgentExecutionStatus.SUCCESS,
            retrieved_chunks_count=len(retrieval_chunks),
            grounding_references=grounding_refs,
            total_risks_detected=len(detected_risks),
            risk_summary_counts=counts_dict,
            detected_risks=detected_risks,
            identified_risks=detected_risks,
            forecast=delivery_forecast,
            delivery_forecast=delivery_forecast,
            executive_risk_statement=summary_statement,
            execution_time_ms=elapsed_ms
        )
