"""
Documentation Generation Agent (Milestone 3 - Requirement 1).

Generates structured, grounded project documentation:
1. User Stories (Agile format: As a [role], I want [feature], So that [benefit] with Acceptance Criteria)
2. Risk Register (Enterprise format: Risk_ID, Title, Category, Severity, Likelihood, Impact, Mitigation, Owner, Status)
3. Action Item Lists (Structured checklist: Item_ID, Task, Assignee, Target Deadline, Priority, Status)

All content is strictly grounded in uploaded project artifacts from the RAG knowledge base.
"""
import re
import time
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

from src.architecture.system_design import RetrievedChunk
from src.rag.retriever import SemanticRetriever
from .base import BaseAgent, BaseAgentResult, SourceReference, AgentExecutionStatus
from .scope_agent import ScopeExtractionAgent
from .risk_forecast_agent import RiskForecastAgent
from .blocker_action_agent import BlockerActionAgent

logger = logging.getLogger(__name__)


# =====================================================================
# Structured Data Models for Generated Documentation
# =====================================================================

class UserStory(BaseModel):
    story_id: str = Field(default_factory=lambda: f"US-{uuid.uuid4().hex[:6].upper()}")
    title: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: List[str] = Field(default_factory=list)
    priority: str = "Medium"  # High, Medium, Low
    category: str = "Functional"  # Functional, Technical, Operations, Risk Mitigation
    source_document: str = "unknown"
    source_reference: Optional[SourceReference] = None


class RiskRegisterEntry(BaseModel):
    risk_id: str = Field(default_factory=lambda: f"RSK-{uuid.uuid4().hex[:6].upper()}")
    risk_title: str
    category: str = "Operational"  # Schedule, Dependency, Staffing, Technology, Safety, Operational
    severity: str = "Medium"        # Critical, High, Medium, Low
    likelihood: str = "Medium"      # High, Medium, Low
    impact: str = "Medium"          # High, Medium, Low
    description: str
    mitigation_strategy: str
    contingency_plan: Optional[str] = None
    owner: str = "Unassigned"
    status: str = "Open"            # Open, Investigating, Mitigated, Monitoring
    source_document: str = "unknown"
    source_reference: Optional[SourceReference] = None


class ActionItemDocumentEntry(BaseModel):
    item_id: str = Field(default_factory=lambda: f"ACT-{uuid.uuid4().hex[:6].upper()}")
    task_description: str
    assignee: str = "Unassigned"
    target_date: Optional[str] = None
    priority: str = "Medium"  # High, Medium, Low
    status: str = "Open"      # Open, Pending, In Progress, Completed
    context: Optional[str] = None
    source_document: str = "unknown"
    source_reference: Optional[SourceReference] = None


class DocumentationGenerationResult(BaseAgentResult):
    """Full structured output of the Documentation Generation Agent."""
    user_stories: List[UserStory] = Field(default_factory=list)
    risk_register: List[RiskRegisterEntry] = Field(default_factory=list)
    action_items: List[ActionItemDocumentEntry] = Field(default_factory=list)
    total_user_stories: int = 0
    total_risks: int = 0
    total_action_items: int = 0
    executive_summary: str = ""
    markdown_export: str = ""


# =====================================================================
# Documentation Generation Agent Implementation
# =====================================================================

class DocumentationGenerationAgent(BaseAgent):
    """
    RAG-grounded documentation agent synthesizing agile user stories, enterprise risk registers,
    and actionable meeting checklists from indexed project knowledge.
    """

    DOC_QUERIES = [
        "project goals objectives requirements deliverables features",
        "risks blockers delays dependencies challenges failures",
        "action items tasks next steps meeting notes responsibilities",
        "system architecture module specifications operations workflow"
    ]

    def __init__(self, retriever: Optional[SemanticRetriever] = None):
        super().__init__(
            name="Documentation Generation Agent",
            role="doc_generator",
            description="Generates grounded User Stories, Risk Registers, and Action-Item Lists from project artifacts."
        )
        self.retriever = retriever or SemanticRetriever()
        self.scope_agent = ScopeExtractionAgent(retriever=self.retriever)
        self.risk_agent = RiskForecastAgent(retriever=self.retriever)
        self.blocker_agent = BlockerActionAgent(retriever=self.retriever)

    def retrieve_context(self, custom_query: Optional[str] = None, top_k: int = 8) -> List[RetrievedChunk]:
        """Gathers targeted RAG chunks across all documentation domains."""
        all_chunks: Dict[str, RetrievedChunk] = {}
        queries = [custom_query] if custom_query else self.DOC_QUERIES

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

    def generate_user_stories(
        self,
        retrieval_chunks: List[RetrievedChunk],
        scope_data: Optional[Any] = None
    ) -> List[UserStory]:
        """Synthesizes structured Agile User Stories from project goals, deliverables, and architecture."""
        user_stories: List[UserStory] = []

        if not scope_data:
            scope_data = self.scope_agent.analyze(retrieval_chunks=retrieval_chunks)

        # 1. Generate Stories from Deliverables
        for d in scope_data.deliverables:
            # Determine appropriate persona
            d_name = d.name.strip()
            d_lower = d_name.lower()
            owner = d.owner if d.owner and d.owner != "Unassigned" else "Team Member"

            if any(k in d_lower for k in ["ingestion", "vector", "embedding", "database", "api", "architecture"]):
                persona = "Software Engineer"
                benefit = "the platform can accurately index and retrieve context across project documents"
                prio = "High"
                cat = "Technical"
            elif any(k in d_lower for k in ["event", "festival", "cultural", "indoor", "approval", "catering"]):
                persona = "Event Coordinator"
                benefit = "the community event executes smoothly with all logistics and approvals secured"
                prio = "High"
                cat = "Event Operations"
            elif any(k in d_lower for k in ["linen", "room", "laundry", "maintenance", "part", "generator"]):
                persona = "Operations Lead"
                benefit = "hotel operations maintain guest service standards and operational continuity"
                prio = "High"
                cat = "Operations"
            elif any(k in d_lower for k in ["forklift", "packaging", "supplier", "warehouse", "inspection"]):
                persona = "Warehouse Supervisor"
                benefit = "warehouse throughput and safety compliance remain uninterrupted"
                prio = "High"
                cat = "Operations"
            elif any(k in d_lower for k in ["pos", "stock", "retail", "inventory", "terminal"]):
                persona = "Store Manager"
                benefit = "store checkouts and inventory levels remain accurate during peak traffic"
                prio = "High"
                cat = "Retail Operations"
            else:
                persona = owner if owner != "Unassigned" else "Project Stakeholder"
                benefit = "project milestones and delivery commitments are satisfied on schedule"
                prio = "Medium"
                cat = "Functional"

            title = f"Implement {d_name}" if not d_name.lower().startswith(("implement", "confirm", "schedule", "prepare", "obtain", "provide")) else d_name.title()

            acceptance_criteria = [
                f"Successfully complete and verify: {d_name}",
                f"Assigned owner ({owner}) reviews and signs off on completion",
                f"Documented in project knowledge repository ({d.source_document})"
            ]

            user_stories.append(
                UserStory(
                    title=title,
                    as_a=persona,
                    i_want=f"to execute and verify '{d_name}'",
                    so_that=benefit,
                    acceptance_criteria=acceptance_criteria,
                    priority=prio,
                    category=cat,
                    source_document=d.source_document,
                    source_reference=d.source_reference
                )
            )

        # 2. Generate Stories from Goals (if not duplicate)
        for g in scope_data.project_goals:
            g_stmt = g.statement.strip()
            if not any(us.i_want.lower() in g_stmt.lower() for us in user_stories) and len(g_stmt) > 15:
                persona = "System Architect" if g.category == "technical" else "Project Lead"
                user_stories.append(
                    UserStory(
                        title=f"Core Capability: {g_stmt[:50]}...",
                        as_a=persona,
                        i_want=f"the system to achieve: {g_stmt}",
                        so_that="the initiative delivers on its primary project objectives",
                        acceptance_criteria=[
                            f"System demonstrably fulfills: {g_stmt}",
                            "All integration and operational checks pass successfully"
                        ],
                        priority="High",
                        category=g.category.title(),
                        source_document=g.source_document,
                        source_reference=g.source_reference
                    )
                )

        return user_stories

    def generate_risk_register(
        self,
        retrieval_chunks: List[RetrievedChunk],
        risk_data: Optional[Any] = None
    ) -> List[RiskRegisterEntry]:
        """Synthesizes structured Enterprise Risk Register from detected risks and vulnerabilities."""
        register: List[RiskRegisterEntry] = []

        if not risk_data:
            risk_data = self.risk_agent.analyze(retrieval_chunks=retrieval_chunks)

        risks_list = getattr(risk_data, 'detected_risks', None) or getattr(risk_data, 'identified_risks', [])
        for r in risks_list:
            raw_sev = getattr(r, 'level', None) or getattr(r, 'severity', 'Medium')
            sev_str = raw_sev.value if hasattr(raw_sev, 'value') else str(raw_sev).upper()
            sev = "Critical" if "CRITICAL" in sev_str else "High" if "HIGH" in sev_str else "Medium" if "MEDIUM" in sev_str else "Low"

            cat_raw = getattr(r, 'category', 'Operational')
            cat_str = cat_raw.value if hasattr(cat_raw, 'value') else str(cat_raw)

            # Derive likelihood and impact
            if sev == "Critical":
                likelihood, impact = "High", "High"
            elif sev == "High":
                likelihood, impact = "Medium", "High"
            elif sev == "Medium":
                likelihood, impact = "Medium", "Medium"
            else:
                likelihood, impact = "Low", "Low"

            reason_str = getattr(r, 'reason', None) or getattr(r, 'rationale', '')
            mitigation = getattr(r, 'suggested_mitigation', None) or getattr(r, 'mitigation_recommendation', None) or f"Monitor {cat_str} closely and establish contingency arrangements."
            contingency = f"Escalate immediately if delay/failure exceeds threshold for {r.title}."

            register.append(
                RiskRegisterEntry(
                    risk_title=r.title,
                    category=cat_str,
                    severity=sev,
                    likelihood=likelihood,
                    impact=impact,
                    description=reason_str,
                    mitigation_strategy=mitigation,
                    contingency_plan=contingency,
                    owner="Risk Lead / Assigned Owner",
                    status="Open",
                    source_document=getattr(r, 'source_document', 'unknown'),
                    source_reference=getattr(r, 'source_reference', None)
                )
            )

        return register

    def generate_action_items(
        self,
        retrieval_chunks: List[RetrievedChunk],
        blocker_data: Optional[Any] = None
    ) -> List[ActionItemDocumentEntry]:
        """Synthesizes structured Action-Item Checklist from meeting minutes and blockers."""
        action_items: List[ActionItemDocumentEntry] = []

        if not blocker_data:
            blocker_data = self.blocker_agent.analyze(retrieval_chunks=retrieval_chunks)

        # 1. Action Items
        for act in blocker_data.action_items:
            prio_val = act.priority.value if hasattr(act.priority, 'value') else str(act.priority).upper()
            prio = "High" if prio_val in ["P0", "P1", "CRITICAL", "HIGH"] else "Medium" if prio_val in ["P2", "MEDIUM"] else "Low"

            action_items.append(
                ActionItemDocumentEntry(
                    task_description=act.task_description,
                    assignee=act.assignee if act.assignee else "Unassigned",
                    target_date=act.due_date,
                    priority=prio,
                    status=act.status.title() if act.status else "Open",
                    context=act.supporting_context,
                    source_document=act.source_document,
                    source_reference=act.source_reference
                )
            )

        # 2. Blockers as Urgent Action Items
        for blk in blocker_data.active_blockers:
            action_items.append(
                ActionItemDocumentEntry(
                    task_description=f"Resolve Blocker: {blk.description}",
                    assignee=blk.owner if blk.owner and blk.owner != "Unassigned" else "Team Lead",
                    target_date="Immediate / Next Sprint",
                    priority="High",
                    status="Open",
                    context=f"Blocker Category: {blk.category}. Related dependency: {blk.related_dependency or 'N/A'}",
                    source_document=blk.source_document,
                    source_reference=blk.source_reference
                )
            )

        return action_items

    def generate_markdown_export(
        self,
        user_stories: List[UserStory],
        risk_register: List[RiskRegisterEntry],
        action_items: List[ActionItemDocumentEntry]
    ) -> str:
        """Generates a complete, publication-ready Markdown document."""
        md = []
        md.append("# 📋 AI Project Intelligence - Grounded Project Documentation\n")
        md.append(f"*Generated on: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}*\n")

        # Section 1: User Stories
        md.append("## 1. 📖 Agile User Stories\n")
        if not user_stories:
            md.append("> *No explicit user stories derived from currently indexed documents.*\n")
        else:
            for s in user_stories:
                md.append(f"### Story `{s.story_id}`: {s.title}")
                md.append(f"- **As a** {s.as_a}")
                md.append(f"- **I want** {s.i_want}")
                md.append(f"- **So that** {s.so_that}")
                md.append(f"- **Priority**: `{s.priority}` | **Category**: `{s.category}` | **Source**: `{s.source_document}`")
                md.append("- **Acceptance Criteria**:")
                for ac in s.acceptance_criteria:
                    md.append(f"  - [ ] {ac}")
                md.append("")

        # Section 2: Risk Register
        md.append("## 2. 🛡️ Enterprise Risk Register\n")
        if not risk_register:
            md.append("> *No active project risks identified in current knowledge base.*\n")
        else:
            md.append("| Risk ID | Title | Category | Severity | Likelihood | Impact | Owner | Mitigation Strategy | Source |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for r in risk_register:
                md.append(f"| `{r.risk_id}` | {r.risk_title} | {r.category} | **{r.severity}** | {r.likelihood} | {r.impact} | {r.owner} | {r.mitigation_strategy} | `{r.source_document}` |")
            md.append("")

        # Section 3: Action Items
        md.append("## 3. ✅ Action Items & Execution Checklist\n")
        if not action_items:
            md.append("> *No active action items extracted from current knowledge base.*\n")
        else:
            md.append("| Item ID | Task Description | Assignee | Due Date | Priority | Status | Source |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for a in action_items:
                due = a.target_date or "Planned"
                md.append(f"| `{a.item_id}` | {a.task_description} | **{a.assignee}** | {due} | `{a.priority}` | `{a.status}` | `{a.source_document}` |")
            md.append("")

        return "\n".join(md)

    def analyze(
        self,
        retrieval_chunks: Optional[List[RetrievedChunk]] = None,
        query_context: Optional[str] = None
    ) -> DocumentationGenerationResult:
        """Executes full documentation generation pipeline over RAG context."""
        start_time = time.perf_counter()

        if retrieval_chunks is None:
            retrieval_chunks = self.retrieve_context(custom_query=query_context)

        if not retrieval_chunks:
            return DocumentationGenerationResult(
                agent_name=self.name,
                agent_role=self.role,
                execution_status=AgentExecutionStatus.NO_DATA,
                notes="No relevant document chunks found in vector database.",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        grounding_refs = self.map_chunks_to_references(retrieval_chunks)

        user_stories = self.generate_user_stories(retrieval_chunks)
        risk_register = self.generate_risk_register(retrieval_chunks)
        action_items = self.generate_action_items(retrieval_chunks)
        markdown_doc = self.generate_markdown_export(user_stories, risk_register, action_items)

        summary = (
            f"Generated {len(user_stories)} Agile User Stories, {len(risk_register)} Risk Register Entries, "
            f"and {len(action_items)} Action Item Checklist records grounded across {len(retrieval_chunks)} retrieved chunks."
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return DocumentationGenerationResult(
            agent_name=self.name,
            agent_role=self.role,
            execution_status=AgentExecutionStatus.SUCCESS,
            retrieved_chunks_count=len(retrieval_chunks),
            grounding_references=grounding_refs,
            user_stories=user_stories,
            risk_register=risk_register,
            action_items=action_items,
            total_user_stories=len(user_stories),
            total_risks=len(risk_register),
            total_action_items=len(action_items),
            executive_summary=summary,
            markdown_export=markdown_doc,
            execution_time_ms=elapsed_ms
        )
