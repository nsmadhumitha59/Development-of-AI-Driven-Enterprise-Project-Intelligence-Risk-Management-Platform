"""
Blocker and Action Item Identification Agent (Milestone 2 - Requirement 3).

Analyzes meeting notes, progress updates, sprint tasks, and project documents via RAG.
Extracts:
- Active Blockers (description, category, severity, owner, related dependency, status, source context)
- Action Items (task description, assignee, due date, priority, status, source context)
- Pending Decisions (decision needed, context, decision maker, urgency, source context)
- Unresolved Issues (summary, affected area, status, source context)
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


class BlockerSeverity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    BLOCKING = "Blocking / Critical"


class ActionItemPriority(str, Enum):
    P0 = "P0 - Blocker"
    P1 = "P1 - High"
    P2 = "P2 - Medium"
    P3 = "P3 - Low"


class BlockerItem(BaseModel):
    blocker_id: str = Field(default_factory=lambda: f"BLK-{uuid.uuid4().hex[:6].upper()}")
    description: str
    category: str = "Dependency"  # Dependency, Access / Permissions, Technical, Process / Approval, Vendor / External, Staffing, Resource, Operational
    severity: BlockerSeverity = BlockerSeverity.HIGH
    impacted_component: str = "General System"
    owner: str = "Unassigned"
    related_dependency: Optional[str] = None
    status: str = "active"  # active, in_progress, resolved
    source_document: str = "unknown"
    supporting_context: Optional[str] = None
    source_reference: Optional[SourceReference] = None


class PendingDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"DEC-{uuid.uuid4().hex[:6].upper()}")
    decision_needed: str
    context: str
    decision_maker: str = "Lead Architect / Product Owner"
    urgency: str = "medium"  # high, medium, low
    source_document: str = "unknown"
    supporting_context: Optional[str] = None
    source_reference: Optional[SourceReference] = None


class UnresolvedIssue(BaseModel):
    issue_id: str = Field(default_factory=lambda: f"ISS-{uuid.uuid4().hex[:6].upper()}")
    summary: str
    affected_area: str = "Project Workflow"
    status: str = "open"  # open, investigating, pending_review
    source_document: str = "unknown"
    supporting_context: Optional[str] = None
    source_reference: Optional[SourceReference] = None


class ActionItem(BaseModel):
    action_id: str = Field(default_factory=lambda: f"ACT-{uuid.uuid4().hex[:6].upper()}")
    task_description: str
    assignee: str = "Unassigned"
    due_date: Optional[str] = None
    priority: ActionItemPriority = ActionItemPriority.P1
    status: str = "open"  # open, in_progress, completed
    source_document: str = "unknown"
    supporting_context: Optional[str] = None
    source_reference: Optional[SourceReference] = None


class BlockerActionResult(BaseAgentResult):
    """Structured output for Blocker & Action Item Identification Agent."""
    active_blockers: List[BlockerItem] = Field(default_factory=list)
    blockers: List[BlockerItem] = Field(default_factory=list)  # Backward-compatible alias
    action_items: List[ActionItem] = Field(default_factory=list)
    pending_decisions: List[PendingDecision] = Field(default_factory=list)
    unresolved_issues: List[UnresolvedIssue] = Field(default_factory=list)
    total_blockers: int = 0
    total_action_items: int = 0
    total_pending_decisions: int = 0
    total_unresolved_issues: int = 0
    empty_blockers_message: Optional[str] = None
    executive_summary: str = ""


# =====================================================================
# Blocker & Action Item Identification Agent Implementation
# =====================================================================

class BlockerActionAgent(BaseAgent):
    """
    RAG-driven agent that parses meeting minutes, standups, and task logs to
    extract action items, active blockers, pending decisions, and unresolved issues.
    """

    BLOCKER_QUERIES = [
        "current blockers",
        "unresolved issues",
        "project dependencies",
        "pending decisions",
        "delayed tasks",
        "blocked tasks",
        "issues preventing progress",
        "meeting action items",
        "sprint task assignment assignee"
    ]

    def __init__(self, retriever: Optional[SemanticRetriever] = None):
        super().__init__(
            name="Blocker & Action Item Identification Agent",
            role="blocker_action_extractor",
            description="Extracts blockers, pending architectural decisions, unresolved issues, and action items with assignees and due dates."
        )
        self.retriever = retriever or SemanticRetriever()

    def retrieve_context(self, custom_query: Optional[str] = None, top_k: int = 8) -> List[RetrievedChunk]:
        """Gathers targeted RAG chunks covering action items, blockers, decisions, and issues."""
        all_chunks: Dict[str, RetrievedChunk] = {}
        queries = [custom_query] if custom_query else self.BLOCKER_QUERIES

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
    ) -> BlockerActionResult:
        """Executes blocker and action item extraction across retrieved document chunks."""
        start_time = time.perf_counter()

        if retrieval_chunks is None:
            retrieval_chunks = self.retrieve_context(custom_query=query_context)

        if not retrieval_chunks:
            return BlockerActionResult(
                agent_name=self.name,
                agent_role=self.role,
                execution_status=AgentExecutionStatus.NO_DATA,
                empty_blockers_message="No active blockers identified from the uploaded documents.",
                notes="No meeting or action item chunks found in vector database.",
                executive_summary="No active blockers identified from the uploaded documents. 0 action items identified.",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        grounding_refs = self.map_chunks_to_references(retrieval_chunks)

        blockers: List[BlockerItem] = []
        pending_decisions: List[PendingDecision] = []
        unresolved_issues: List[UnresolvedIssue] = []
        action_items: List[ActionItem] = []

        explicit_assignee_pattern = re.compile(
            r"\b(?:Assignee|Owner|Lead|Assigned to|Action by|Who):\s*([A-Za-z\s]+?)(?:;|\n|,|\.|$)",
            re.IGNORECASE
        )
        role_lead_pattern = re.compile(
            r"^([A-Za-z\s\-\*•]+(?:lead|coordinator|manager|supervisor|team|engineer|developer|specialist|owner|architect|admin)):\s*(.+)$",
            re.IGNORECASE
        )
        explicit_due_pattern = re.compile(
            r"\b(?:Due|Deadline|Target|By):\s*([A-Za-z0-9\-\/]+(?:\s+\d{1,2}(?:,\s*20\d{2})?)?)",
            re.IGNORECASE
        )

        blocker_indicators = [
            "blocker", "blocked", "blocked by", "dependency preventing progress",
            "unable to proceed", "pending approval", "waiting for", "waiting on",
            "delayed because", "dependency not completed", "access unavailable",
            "resource unavailable", "vendor dependency", "technical issue preventing progress",
            "stalled", "impediment", "not approved", "not confirmed", "unavailable because",
            "outage", "has not finalized", "has not received", "has not completed"
        ]

        false_blocker_terms = [
            "blocker analysis", "blocker agent", "blocker identification agent",
            "blockers & action items", "blocker detection", "blocker evaluation",
            "and blocker analysis"
        ]

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

                # Detect section transitions
                if re.match(r"^(?:active\s+)?blockers?[:\s]*$", lower_line):
                    current_section = "blockers"
                    continue
                elif re.match(r"^(?:current\s+issues?|unresolved\s+issues?)[:\s]*$", lower_line):
                    current_section = "issues"
                    continue
                elif re.match(r"^(?:pending\s+decisions?|decisions?\s+needed)[:\s]*$", lower_line):
                    current_section = "decisions"
                    continue
                elif re.match(r"^(?:action\s+items?|current\s+actions?|next\s+steps?)[:\s]*$", lower_line):
                    current_section = "actions"
                    continue
                elif re.match(r"^(?:potential\s+risks?|risks?\s+identified|objectives?|goals?)[:\s]*$", lower_line):
                    current_section = None

                # 1. Blockers extraction
                is_false_blocker = any(fb in lower_line for fb in false_blocker_terms)
                is_explicit_blocker = (
                    not is_false_blocker and (
                        current_section == "blockers" or
                        (any(k in lower_line for k in blocker_indicators) and current_section != "actions")
                    )
                )

                if is_explicit_blocker and len(line) > 8 and current_section != "actions":
                    clean_desc = line
                    for prefix in [r"^(?:blocker:?|impediment:?|current issue:?)\s*", r"^[•\-\*]\s*"]:
                        clean_desc = re.sub(prefix, "", clean_desc, flags=re.IGNORECASE).strip()

                    if len(clean_desc) > 8 and clean_desc.lower() not in ["blockers", "current issues"]:
                        if not any(b.description.lower() == clean_desc.lower() for b in blockers):
                            if any(w in lower_line for w in ["vendor", "supplier", "third party"]):
                                cat = "Vendor / External"
                            elif any(w in lower_line for w in ["access", "permission", "vpc", "security", "token"]):
                                cat = "Access / Permissions"
                            elif any(w in lower_line for w in ["staff", "hire", "shift", "team", "resource", "volunteer"]):
                                cat = "Staffing / Resource"
                            elif any(w in lower_line for w in ["approval", "approved", "decision", "confirm"]):
                                cat = "Process / Approval"
                            elif any(w in lower_line for w in ["cache", "server", "timeout", "cluster", "generator", "test", "hardware"]):
                                cat = "Technical"
                            else:
                                cat = "Dependency"

                            sev = BlockerSeverity.BLOCKING if any(s in lower_line for s in ["critical", "severe", "outage", "unavailable", "blocking"]) else BlockerSeverity.HIGH
                            component = chunk.metadata.section_title or filename

                            owner_m = explicit_assignee_pattern.search(line)
                            owner_val = owner_m.group(1).strip() if owner_m else "Unassigned"

                            dep_val = None
                            if "waiting for" in lower_line:
                                dep_val = line[lower_line.find("waiting for"):]
                            elif "blocked by" in lower_line:
                                dep_val = line[lower_line.find("blocked by"):]
                            elif "because" in lower_line:
                                dep_val = line[lower_line.find("because"):]

                            blockers.append(
                                BlockerItem(
                                    description=clean_desc,
                                    category=cat,
                                    severity=sev,
                                    impacted_component=component,
                                    owner=owner_val,
                                    related_dependency=dep_val,
                                    status="active",
                                    source_document=filename,
                                    supporting_context=line,
                                    source_reference=ref
                                )
                            )

                # 2. Pending Decisions
                is_decision = (
                    current_section == "decisions" or
                    any(k in lower_line for k in ["decision needed", "pending decision", "to decide", "needs decision", "decision required", "options to consider"])
                )
                if is_decision and len(line) > 10 and current_section != "actions":
                    clean_dec = line
                    for prefix in [r"^(?:pending\s+decision:?|decision\s+needed:?|decision:?)\s*", r"^[•\-\*]\s*"]:
                        clean_dec = re.sub(prefix, "", clean_dec, flags=re.IGNORECASE).strip()

                    if len(clean_dec) > 10 and not any(d.decision_needed.lower() == clean_dec.lower() for d in pending_decisions):
                        urgency_val = "high" if any(u in lower_line for u in ["urgent", "immediate", "asap", "critical", "friday", "today"]) else "medium"
                        pending_decisions.append(
                            PendingDecision(
                                decision_needed=clean_dec,
                                context=line,
                                decision_maker="Lead Architect / Product Owner",
                                urgency=urgency_val,
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )

                # 3. Unresolved Issues (that are distinct from explicit blockers)
                if current_section == "issues" or (any(k in lower_line for k in ["unresolved", "open problem", "investigating bug", "connection timeouts", "stock discrepancy", "pos downtime"]) and not is_explicit_blocker):
                    clean_issue = line
                    for prefix in [r"^(?:current\s+issue:?|issue:?|unresolved:?)\s*", r"^[•\-\*]\s*", r"^row\s+\d+:?\s*"]:
                        clean_issue = re.sub(prefix, "", clean_issue, flags=re.IGNORECASE).strip()

                    if len(clean_issue) > 10 and not any(i.summary.lower() == clean_issue.lower() for i in unresolved_issues) and not any(b.description.lower() == clean_issue.lower() for b in blockers):
                        unresolved_issues.append(
                            UnresolvedIssue(
                                summary=clean_issue,
                                affected_area=filename,
                                status="open",
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )

                # 4. Action Items (Tasks / next steps to be done)
                is_action = (
                    current_section == "actions" or
                    any(k in lower_line for k in ["action item", "action items:", "todo", "next step", "next steps:", "task:", "task_id:", "current actions", "will arrange", "will perform", "will contact"]) or
                    ("task_id:" in lower_line and "title:" in lower_line) or
                    bool(role_lead_pattern.match(line))
                )

                if is_action and len(line) > 8 and current_section != "blockers":
                    assignee_match = explicit_assignee_pattern.search(line)
                    role_match = role_lead_pattern.match(line)

                    if role_match:
                        raw_role = role_match.group(1).strip()
                        assignee_val = re.sub(r"^[•\-\*]\s*", "", raw_role).strip()
                        clean_task = role_match.group(2).strip()
                    elif assignee_match:
                        assignee_val = assignee_match.group(1).strip()
                        clean_task = line
                    else:
                        assignee_val = "Unassigned"
                        clean_task = line

                    due_match = explicit_due_pattern.search(line)
                    if due_match:
                        due_date_val = due_match.group(1).strip().rstrip(".;,")
                    else:
                        dates_found = re.findall(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", line)
                        due_date_val = dates_found[0] if dates_found else None

                    prio = ActionItemPriority.P0 if "critical" in lower_line or "p0" in lower_line else \
                           ActionItemPriority.P1 if "high" in lower_line or "p1" in lower_line or "urgent" in lower_line else \
                           ActionItemPriority.P2

                    status_val = "completed" if "completed" in lower_line else "in_progress" if "in progress" in lower_line else "open"

                    for prefix in [
                        r"^(?:action\s+items?:?|current\s+actions?:?|todo:?|next\s+steps?:?|row\s+\d+:?)\s*",
                        r"^[•\-\*]\s*",
                        r"^Task_ID:\s*[^;]+;\s*Title:\s*"
                    ]:
                        clean_task = re.sub(prefix, "", clean_task, flags=re.IGNORECASE).strip()

                    clean_task = re.split(r"(?:\.|\;)\s*(?:Assignee|Due|Status):", clean_task, flags=re.IGNORECASE)[0].strip()

                    if len(clean_task) > 6 and not any(a.task_description.lower() == clean_task.lower() for a in action_items) and not any(b.description.lower() == clean_task.lower() for b in blockers):
                        action_items.append(
                            ActionItem(
                                task_description=clean_task,
                                assignee=assignee_val,
                                due_date=due_date_val,
                                priority=prio,
                                status=status_val,
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )

        # Build clean summary
        empty_blockers_msg = None
        if not blockers:
            empty_blockers_msg = "No active blockers identified from the uploaded documents."
            summary_str = f"No active blockers identified from the uploaded documents. {len(action_items)} action items identified across {len(retrieval_chunks)} knowledge chunks."
        else:
            summary_str = (
                f"Identified {len(blockers)} active blockers, {len(action_items)} action items, "
                f"{len(pending_decisions)} pending decisions, and {len(unresolved_issues)} unresolved issues "
                f"across {len(retrieval_chunks)} knowledge chunks."
            )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return BlockerActionResult(
            agent_name=self.name,
            agent_role=self.role,
            execution_status=AgentExecutionStatus.SUCCESS,
            retrieved_chunks_count=len(retrieval_chunks),
            grounding_references=grounding_refs,
            active_blockers=blockers,
            blockers=blockers,
            action_items=action_items,
            pending_decisions=pending_decisions,
            unresolved_issues=unresolved_issues,
            total_blockers=len(blockers),
            total_action_items=len(action_items),
            total_pending_decisions=len(pending_decisions),
            total_unresolved_issues=len(unresolved_issues),
            empty_blockers_message=empty_blockers_msg,
            executive_summary=summary_str,
            execution_time_ms=elapsed_ms
        )
