"""
Scope and Deliverable Extraction Agent (Milestone 2 - Requirement 1).

Retrieves and extracts:
- Project goals & objectives (supporting varied phrasing without requiring exact headings)
- Scope boundaries (in-scope, out-of-scope, constraints, assumptions)
- Deliverables & key actionable tasks with owners and due dates
- Milestones & events
- Timelines & deadlines
- Responsibilities / owners
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

logger = logging.getLogger(__name__)


# =====================================================================
# Structured Data Models for Scope & Deliverables
# =====================================================================

class ProjectGoal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"GOL-{uuid.uuid4().hex[:6].upper()}")
    statement: str
    supporting_context: Optional[str] = None
    category: str = "strategic"  # strategic, technical, operational, business, event
    priority: str = "high"       # high, medium, low
    source_document: str = "unknown"
    source_reference: Optional[SourceReference] = None


class ScopeBoundary(BaseModel):
    in_scope: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class DeliverableItem(BaseModel):
    deliverable_id: str = Field(default_factory=lambda: f"DEL-{uuid.uuid4().hex[:6].upper()}")
    name: str
    description: str
    owner: str = "Unassigned"
    target_date: Optional[str] = None
    status: str = "pending"  # completed, in_progress, pending, planned
    source_document: str = "unknown"
    supporting_context: Optional[str] = None
    source_reference: Optional[SourceReference] = None


class MilestoneItem(BaseModel):
    milestone_id: str = Field(default_factory=lambda: f"MLS-{uuid.uuid4().hex[:6].upper()}")
    title: str
    target_timeline: Optional[str] = None
    deliverables: List[str] = Field(default_factory=list)
    owner: str = "Project Team"
    status: str = "planned"
    source_document: str = "unknown"
    supporting_context: Optional[str] = None
    source_reference: Optional[SourceReference] = None


class TimelineItem(BaseModel):
    timeline_id: str = Field(default_factory=lambda: f"TL-{uuid.uuid4().hex[:6].upper()}")
    milestone_or_task: str
    target_deadline: str
    status: str = "planned"
    source_document: str = "unknown"
    supporting_context: Optional[str] = None
    source_reference: Optional[SourceReference] = None


class ResponsibilityAssignment(BaseModel):
    role_or_person: str
    responsibility_area: str
    associated_deliverables: List[str] = Field(default_factory=list)
    source_document: str = "unknown"
    source_reference: Optional[SourceReference] = None


class ScopeExtractionResult(BaseAgentResult):
    """Full structured output of the Scope and Deliverable Extraction Agent."""
    project_title: Optional[str] = None
    project_goals: List[ProjectGoal] = Field(default_factory=list)
    goals: List[ProjectGoal] = Field(default_factory=list)  # Backward-compatible alias
    deliverables: List[DeliverableItem] = Field(default_factory=list)
    milestones: List[MilestoneItem] = Field(default_factory=list)
    timelines: List[TimelineItem] = Field(default_factory=list)
    responsible_owners: List[ResponsibilityAssignment] = Field(default_factory=list)
    responsibilities: List[ResponsibilityAssignment] = Field(default_factory=list)  # Backward-compatible alias
    scope: ScopeBoundary = Field(default_factory=ScopeBoundary)
    summary: str = ""
    empty_goals_message: Optional[str] = None


# =====================================================================
# Scope and Deliverable Extraction Agent Implementation
# =====================================================================

class ScopeExtractionAgent(BaseAgent):
    """
    Extracts goals, boundaries, deliverables, milestones, deadlines, and owners
    by retrieving and analyzing project artifacts from the RAG knowledge base.
    """

    SCOPE_QUERIES = [
        "project goals and objectives",
        "project purpose and expected outcomes",
        "project deliverables and key outputs",
        "project milestones and schedule",
        "project timeline and deadlines",
        "project responsibilities and task assignments",
        "action items tasks next steps",
        "event dates and planning milestones",
        "project requirements in-scope out-of-scope constraints"
    ]

    def __init__(self, retriever: Optional[SemanticRetriever] = None):
        super().__init__(
            name="Scope & Deliverable Extraction Agent",
            role="scope_extractor",
            description="Extracts goals, scope boundaries, deliverables, milestones, timelines, and owners from project documents."
        )
        self.retriever = retriever or SemanticRetriever()

    def retrieve_context(self, custom_query: Optional[str] = None, top_k: int = 8) -> List[RetrievedChunk]:
        """Gathers targeted RAG chunks covering scope, goals, deliverables, and assignments."""
        all_chunks: Dict[str, RetrievedChunk] = {}
        queries = [custom_query] if custom_query else self.SCOPE_QUERIES

        for q in queries:
            if not q:
                continue
            chunks = self.retriever.retrieve(query=q, top_k=top_k)
            for c in chunks:
                # Key by normalized content to prevent duplicate chunk flooding across redundant uploads
                content_key = c.content.strip().lower()
                if content_key not in all_chunks or c.score > all_chunks[content_key].score:
                    all_chunks[content_key] = c

        sorted_chunks = sorted(all_chunks.values(), key=lambda x: x.score, reverse=True)
        return sorted_chunks[:max(top_k * 4, 30)]

    def analyze(
        self,
        retrieval_chunks: Optional[List[RetrievedChunk]] = None,
        query_context: Optional[str] = None
    ) -> ScopeExtractionResult:
        """
        Processes RAG context chunks to extract structured scope elements with grounding.
        """
        start_time = time.perf_counter()

        if retrieval_chunks is None:
            retrieval_chunks = self.retrieve_context(custom_query=query_context)

        if not retrieval_chunks:
            return ScopeExtractionResult(
                agent_name=self.name,
                agent_role=self.role,
                execution_status=AgentExecutionStatus.NO_DATA,
                empty_goals_message="No explicit project goals found in the uploaded documents.",
                notes="No relevant document chunks found in vector database.",
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        grounding_refs = self.map_chunks_to_references(retrieval_chunks)

        extracted_goals: List[ProjectGoal] = []
        in_scope_items: List[str] = []
        out_of_scope_items: List[str] = []
        constraints_items: List[str] = []
        assumptions_items: List[str] = []
        deliverables_list: List[DeliverableItem] = []
        milestones_list: List[MilestoneItem] = []
        timelines_list: List[TimelineItem] = []
        assignments_map: Dict[str, ResponsibilityAssignment] = {}
        project_title = None

        date_pattern = re.compile(
            r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|Q[1-4][- ]?20\d{2}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+20\d{2}|\b(?:September|October|November|December|January|February|March|April|May|June|July|August)\s+20\d{2}|\b(?:by\s+)?(?:Friday|Monday|Tuesday|Wednesday|Thursday|Saturday|Sunday))\b",
            re.IGNORECASE
        )
        explicit_assignee_pattern = re.compile(
            r"\b(?:Assignee|Owner|Lead|Assigned to|Action by|Who):\s*([A-Za-z\s]+?)(?:;|\n|,|\.|$)",
            re.IGNORECASE
        )
        role_lead_pattern = re.compile(
            r"^([A-Za-z\s\-\*•]+(?:lead|coordinator|manager|supervisor|team|engineer|developer|specialist|owner|architect|admin)):\s*(.+)$",
            re.IGNORECASE
        )
        status_pattern = re.compile(
            r"\b(?:Status):\s*(Completed|In Progress|Pending|Blocked|Active|In Review|Open)\b",
            re.IGNORECASE
        )

        goal_phrases = [
            "project goal", "goals:", "goal:", "primary goal", "secondary goal",
            "objective", "objectives:", "project objective", "business objective", "key objective",
            "purpose", "purpose:", "purpose of the", "aim", "aim is", "aims to", "aim to", "aimed at", "primary aim",
            "project intends to", "intends to", "intended to",
            "the system should", "system should", "system will", "the system will", "system shall",
            "the project will", "project will",
            "expected outcome", "expected outcomes", "desired outcome",
            "focuses on", "mission", "vision"
        ]

        def add_deliverable(name: str, desc: str, owner: str, target_dt: Optional[str], status: str, filename: str, ref: SourceReference):
            clean_name = name.strip().rstrip(".;,")
            if not clean_name or len(clean_name) < 4:
                return
            if not any(d.name.lower() == clean_name.lower() for d in deliverables_list):
                deliverables_list.append(
                    DeliverableItem(
                        name=clean_name,
                        description=desc,
                        owner=owner or "Unassigned",
                        target_date=target_dt,
                        status=status or "pending",
                        source_document=filename,
                        supporting_context=desc,
                        source_reference=ref
                    )
                )
                t_date = target_dt or "Planned"
                if not any(t.milestone_or_task.lower() == clean_name.lower() for t in timelines_list):
                    timelines_list.append(
                        TimelineItem(
                            milestone_or_task=clean_name,
                            target_deadline=t_date,
                            status=status or "planned",
                            source_document=filename,
                            supporting_context=desc,
                            source_reference=ref
                        )
                    )

                if owner and owner != "Unassigned":
                    if owner not in assignments_map:
                        assignments_map[owner] = ResponsibilityAssignment(
                            role_or_person=owner,
                            responsibility_area=f"Deliverables & Workstreams ({filename})",
                            associated_deliverables=[clean_name],
                            source_document=filename,
                            source_reference=ref
                        )
                    else:
                        if clean_name not in assignments_map[owner].associated_deliverables:
                            assignments_map[owner].associated_deliverables.append(clean_name)

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

            # 1. Project Title Detection
            if not project_title:
                title_match = re.search(r"(?:Project|System|Charter|Specification|Event|Report):\s*([^\n\.;|]+)", text, re.IGNORECASE)
                if title_match:
                    project_title = title_match.group(1).strip()
                elif "AI Project Intelligence" in text:
                    project_title = "AI Project Intelligence & Risk Advisor"
                elif "Hotel Operations" in text or "HOTEL OPERATIONS" in text:
                    project_title = "Hotel Operations Management"
                elif "Community Event" in text or "Cultural Festival" in text:
                    project_title = "Community Event Planning"
                elif "Warehouse Operations" in text:
                    project_title = "Warehouse Operations"
                elif "Retail Store" in text or "retail_store" in text:
                    project_title = "Retail Store Risk Management"

            raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
            current_section_mode = None

            # Check Event / Date headers for Milestones & Timelines
            event_match = re.search(r"Event:\s*([^|;\n]+)\s*\|\s*Date:\s*([^;\n]+)", text, re.IGNORECASE)
            if event_match:
                e_name = event_match.group(1).strip()
                e_date = event_match.group(2).strip()
                if not any(m.title.lower() == e_name.lower() for m in milestones_list):
                    milestones_list.append(
                        MilestoneItem(
                            title=e_name,
                            target_timeline=e_date,
                            owner="Event Lead / Project Team",
                            status="planned",
                            source_document=filename,
                            supporting_context=text[:150],
                            source_reference=ref
                        )
                    )
                    timelines_list.append(
                        TimelineItem(
                            milestone_or_task=e_name,
                            target_deadline=e_date,
                            status="planned",
                            source_document=filename,
                            supporting_context=text[:150],
                            source_reference=ref
                        )
                    )

            date_header_match = re.search(r"(?:Date|Reporting Period|Period):\s*([A-Za-z0-9\s,]+(?:20\d{2})?)", text, re.IGNORECASE)
            doc_period_date = None
            if date_header_match:
                doc_period_date = date_header_match.group(1).strip()
                if not event_match:
                    milestone_title = f"{chunk.metadata.section_title or filename.split('.')[0].replace('_', ' ').title()} Period"
                    if not any(t.target_deadline == doc_period_date for t in timelines_list) and len(doc_period_date) > 3:
                        timelines_list.append(
                            TimelineItem(
                                milestone_or_task=milestone_title,
                                target_deadline=doc_period_date,
                                status="active",
                                source_document=filename,
                                supporting_context=text[:120],
                                source_reference=ref
                            )
                        )

            for line in raw_lines:
                lower_line = line.lower()

                # Check section headings
                if re.match(r"^(?:project\s+)?(?:objectives?|goals?|purpose|expected\s+outcomes?)[:\s]*$", lower_line):
                    current_section_mode = "goals"
                    continue
                elif re.match(r"^(?:key\s+)?deliverables?[:\s]*$", lower_line):
                    current_section_mode = "deliverables"
                    continue
                elif re.match(r"^(?:action\s+items?|current\s+actions?|tasks?|sprint\s+tasks?)[:\s]*$", lower_line):
                    current_section_mode = "actions"
                    continue
                elif re.match(r"^(?:in-scope|scope)[:\s]*$", lower_line):
                    current_section_mode = "in_scope"
                    continue
                elif re.match(r"^(?:out-of-scope|excluded)[:\s]*$", lower_line):
                    current_section_mode = "out_of_scope"
                    continue
                elif re.match(r"^(?:constraints?|restrictions?)[:\s]*$", lower_line):
                    current_section_mode = "constraints"
                    continue
                elif re.match(r"^(?:potential\s+risks?|risks?\s+identified|blockers?|current\s+issues?)[:\s]*$", lower_line):
                    current_section_mode = None

                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
                eval_candidates = [line] if len(sentences) <= 1 else [line] + sentences

                # 1. Goals & Objectives Extraction
                for cand in eval_candidates:
                    cand_lower = cand.lower()

                    is_goal = any(p in cand_lower for p in goal_phrases) or (current_section_mode == "goals" and len(cand) > 10)
                    if is_goal and len(cand) > 15 and current_section_mode != "actions":
                        clean_goal = cand
                        for prefix_pattern in [
                            r"^(?:project\s+)?(?:goals?|objectives?|purpose|aim|mission|vision|expected\s+outcome)[:\s-]*",
                            r"^(?:\d+[\.\)]|\*|-|•)\s*"
                        ]:
                            clean_goal = re.sub(prefix_pattern, "", clean_goal, flags=re.IGNORECASE).strip()

                        if len(clean_goal) > 15 and not any(g.statement.lower() == clean_goal.lower() for g in extracted_goals):
                            if any(t in cand_lower for t in ["code", "api", "model", "vector", "architecture", "system", "database"]):
                                cat = "technical"
                            elif any(t in cand_lower for t in ["event", "festival", "community", "volunteer"]):
                                cat = "event"
                            elif any(t in cand_lower for t in ["business", "revenue", "cost", "market", "customer"]):
                                cat = "business"
                            elif any(t in cand_lower for t in ["operation", "maintenance", "shift", "warehouse", "inventory"]):
                                cat = "operational"
                            else:
                                cat = "strategic"

                            extracted_goals.append(
                                ProjectGoal(
                                    statement=clean_goal,
                                    supporting_context=line,
                                    category=cat,
                                    priority="high",
                                    source_document=filename,
                                    source_reference=ref
                                )
                            )

                # 2. Scope Boundaries
                if any(k in lower_line for k in ["in-scope", "in scope", "scope includes", "features:"]) or current_section_mode == "in_scope":
                    clean_item = re.sub(r"^(?:in-scope:?|in scope:?|•|-|\*)\s*", "", line, flags=re.IGNORECASE).strip()
                    if len(clean_item) > 10 and clean_item not in in_scope_items and clean_item != "in-scope":
                        in_scope_items.append(clean_item)
                        add_deliverable(clean_item, line, "Project Team", doc_period_date, "planned", filename, ref)
                elif any(k in lower_line for k in ["out-of-scope", "out of scope", "excluded", "do not implement", "future phase"]) or current_section_mode == "out_of_scope":
                    clean_item = re.sub(r"^(?:out-of-scope:?|out of scope:?|•|-|\*)\s*", "", line, flags=re.IGNORECASE).strip()
                    if len(clean_item) > 10 and clean_item not in out_of_scope_items and clean_item != "out-of-scope":
                        out_of_scope_items.append(clean_item)
                elif any(k in lower_line for k in ["constraint", "limitation", "restricted to", "strict restriction"]) or current_section_mode == "constraints":
                    clean_item = re.sub(r"^(?:constraint:?|restrictions?:?|•|-|\*)\s*", "", line, flags=re.IGNORECASE).strip()
                    if len(clean_item) > 10 and clean_item not in constraints_items and clean_item != "constraints":
                        constraints_items.append(clean_item)

                # 3. Milestones & Releases
                if any(k in lower_line for k in ["milestone", "phase", "sprint", "release"]):
                    m_dates = date_pattern.findall(line)
                    m_date_str = m_dates[0] if m_dates else (doc_period_date or "Planned")
                    clean_m_name = line
                    for pfix in [r"^(?:\d+[\.\)]|\*|-|•)\s*", r"^Phase:\s*", r"^Milestone:\s*"]:
                        clean_m_name = re.sub(pfix, "", clean_m_name, flags=re.IGNORECASE).strip()

                    # Extract milestone title up to punctuation or focuses on
                    m_title = re.split(r"(?:focuses on|includes|consists of|;|:|\.)", clean_m_name, flags=re.IGNORECASE)[0].strip()
                    if len(m_title) < 4:
                        m_title = clean_m_name.split(".")[0].split(";")[0].strip()

                    if len(m_title) >= 4 and not any(m.title.lower() == m_title.lower() for m in milestones_list):
                        m_status = "active" if "active" in lower_line or "in progress" in lower_line else "planned"
                        milestones_list.append(
                            MilestoneItem(
                                title=m_title,
                                target_timeline=m_date_str,
                                owner="Project Team",
                                status=m_status,
                                source_document=filename,
                                supporting_context=line,
                                source_reference=ref
                            )
                        )
                        if not any(t.milestone_or_task.lower() == m_title.lower() for t in timelines_list):
                            timelines_list.append(
                                TimelineItem(
                                    milestone_or_task=m_title,
                                    target_deadline=m_date_str,
                                    status=m_status,
                                    source_document=filename,
                                    supporting_context=line,
                                    source_reference=ref
                                )
                            )

                # 4. Extract Deliverables from Lists & Compound Sentences ("focuses on X, Y, and Z")
                focus_match = re.search(r"(?:focuses on|deliverables include|includes|provides|consists of)\s+([^.]+)", line, re.IGNORECASE)
                if focus_match:
                    items_str = focus_match.group(1).strip()
                    sub_items = re.split(r",\s*(?:and\s+)?|\s+and\s+", items_str)
                    for sub in sub_items:
                        sub_clean = sub.strip().rstrip(".;")
                        if len(sub_clean) > 5 and not any(k in sub_clean.lower() for k in ["the following", "various"]):
                            add_deliverable(
                                name=sub_clean,
                                desc=f"Deliverable component: {sub_clean} ({line})",
                                owner="Project Team",
                                target_dt=doc_period_date or "Planned",
                                status="in_progress" if "focuses on" in line.lower() else "planned",
                                filename=filename,
                                ref=ref
                            )

                # 5. Deliverables & Actionable Tasks
                is_deliverable = (
                    current_section_mode in ["deliverables", "actions"] or
                    any(k in lower_line for k in ["deliverable", "deliverables include", "task", "task_id:", "action item", "current actions", "will arrange", "will perform", "will contact", "title:", "feature", "module", "row "]) or
                    bool(role_lead_pattern.match(line)) or
                    (bool(explicit_assignee_pattern.search(line)) and bool(date_pattern.search(line)))
                )

                if is_deliverable and len(line) > 8:
                    assignee_match = explicit_assignee_pattern.search(line)
                    role_match = role_lead_pattern.match(line)
                    clean_item_name = line

                    if role_match:
                        raw_role = role_match.group(1).strip()
                        owner_val = re.sub(r"^[•\-\*]\s*", "", raw_role).strip()
                        clean_item_name = role_match.group(2).strip()
                    elif assignee_match:
                        owner_val = assignee_match.group(1).strip()
                    else:
                        owner_val = "Unassigned"

                    status_match = status_pattern.search(line)
                    status_val = status_match.group(1).lower().replace(" ", "_") if status_match else "pending"

                    d_dates = date_pattern.findall(line)
                    target_dt = d_dates[0] if d_dates else doc_period_date

                    for prefix_pattern in [
                        r"^(?:action\s+items?:?|current\s+actions?:?|deliverables?\s*(?:include|are|:)?|todo:?|next\s+steps?:?|row\s+\d+:?)\s*",
                        r"^[•\-\*]\s*",
                        r"^Task_ID:\s*[^;]+;\s*Title:\s*"
                    ]:
                        clean_item_name = re.sub(prefix_pattern, "", clean_item_name, flags=re.IGNORECASE).strip()

                    title_part = clean_item_name.split(";")[0].split(".")[0].strip()
                    if len(title_part) > 5:
                        add_deliverable(
                            name=title_part,
                            desc=line,
                            owner=owner_val,
                            target_dt=target_dt,
                            status=status_val,
                            filename=filename,
                            ref=ref
                        )

        # Fallback in-scope if empty
        if not in_scope_items and deliverables_list:
            in_scope_items = [d.name for d in deliverables_list[:5]]

        # Ensure all milestones are in timelines
        for m in milestones_list:
            if not any(t.milestone_or_task.lower() == m.title.lower() for t in timelines_list):
                timelines_list.append(
                    TimelineItem(
                        milestone_or_task=m.title,
                        target_deadline=m.target_timeline or "Planned",
                        status=m.status,
                        source_document=m.source_document,
                        supporting_context=m.supporting_context,
                        source_reference=m.source_reference
                    )
                )

        empty_goals_msg = None
        if not extracted_goals:
            empty_goals_msg = "No explicit project goals found in the uploaded documents."

        summary_text = (
            f"Extracted {len(extracted_goals)} project goals, {len(deliverables_list)} deliverables, "
            f"{len(milestones_list)} milestones, {len(timelines_list)} deadlines, and {len(assignments_map)} responsible owners across "
            f"{len(retrieval_chunks)} retrieved knowledge chunks."
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ScopeExtractionResult(
            agent_name=self.name,
            agent_role=self.role,
            execution_status=AgentExecutionStatus.SUCCESS,
            retrieved_chunks_count=len(retrieval_chunks),
            grounding_references=grounding_refs,
            project_title=project_title or "Project Workspace",
            project_goals=extracted_goals,
            goals=extracted_goals,
            scope=ScopeBoundary(
                in_scope=in_scope_items,
                out_of_scope=out_of_scope_items,
                constraints=constraints_items,
                assumptions=assumptions_items
            ),
            deliverables=deliverables_list,
            milestones=milestones_list,
            timelines=timelines_list,
            responsible_owners=list(assignments_map.values()),
            responsibilities=list(assignments_map.values()),
            summary=summary_text,
            empty_goals_message=empty_goals_msg,
            notes=empty_goals_msg,
            execution_time_ms=elapsed_ms
        )
