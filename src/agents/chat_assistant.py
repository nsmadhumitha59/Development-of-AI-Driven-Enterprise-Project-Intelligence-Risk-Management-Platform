"""
Conversational Project Intelligence Assistant (Milestone 3 - Requirement 3).

RAG-powered interactive conversational assistant providing grounded answers to project queries:
- "Are we on track?"
- "What are our biggest risks?"
- "What are the current blockers?"
- "What are the pending action items?"
- "What are the project deliverables?"
- Ad-hoc semantic search and synthesis over uploaded PDF, DOCX, CSV, and TXT artifacts.

Strictly grounded in vector store retrieval with source references; refuses to hallucinate when data is missing.
"""
import re
import time
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from src.architecture.system_design import RetrievedChunk
from src.rag.retriever import SemanticRetriever
from .base import BaseAgent, BaseAgentResult, SourceReference, AgentExecutionStatus
from .scope_agent import ScopeExtractionAgent
from .risk_forecast_agent import RiskForecastAgent
from .blocker_action_agent import BlockerActionAgent
from .health_scorer import ProjectHealthScorer

logger = logging.getLogger(__name__)


# =====================================================================
# Structured Data Models for Chat
# =====================================================================

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    source_references: List[SourceReference] = Field(default_factory=list)


class ChatQueryRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    session_history: Optional[List[Dict[str, str]]] = None


class ChatQueryResponse(BaseModel):
    message_id: str = Field(default_factory=lambda: f"MSG-{uuid.uuid4().hex[:6].upper()}")
    conversation_id: str
    question: str
    answer: str
    source_references: List[SourceReference] = Field(default_factory=list)
    retrieved_chunks_count: int = 0
    grounded_document_names: List[str] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0


# =====================================================================
# Conversational Assistant Implementation
# =====================================================================

class ProjectIntelligenceChatAssistant(BaseAgent):
    """
    Synthesizes conversational responses to project queries by leveraging
    RAG semantic retrieval and multi-agent domain intelligence.
    """

    def __init__(self, retriever: Optional[SemanticRetriever] = None):
        super().__init__(
            name="Project Intelligence Conversational Assistant",
            role="chat_assistant",
            description="Answers natural language project queries grounded in RAG document knowledge."
        )
        self.retriever = retriever or SemanticRetriever()
        self.scope_agent = ScopeExtractionAgent(retriever=self.retriever)
        self.risk_agent = RiskForecastAgent(retriever=self.retriever)
        self.blocker_agent = BlockerActionAgent(retriever=self.retriever)
        self.health_scorer = ProjectHealthScorer(retriever=self.retriever)

    def retrieve_context(self, custom_query: Optional[str] = None, top_k: int = 6) -> List[RetrievedChunk]:
        """Gathers targeted chunks for the specific chat question."""
        if not custom_query:
            return []
        chunks = self.retriever.retrieve(query=custom_query, top_k=top_k)
        # Content-based deduplication
        deduped: Dict[str, RetrievedChunk] = {}
        for c in chunks:
            k = c.content.strip().lower()
            if k not in deduped or c.score > deduped[k].score:
                deduped[k] = c
        return sorted(deduped.values(), key=lambda x: x.score, reverse=True)

    def answer_question(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        session_history: Optional[List[Dict[str, str]]] = None
    ) -> ChatQueryResponse:
        """
        Processes a natural language question and returns a grounded answer with citations.
        """
        start_time = time.perf_counter()
        conv_id = conversation_id or f"CONV-{uuid.uuid4().hex[:6].upper()}"
        q_clean = question.strip()
        q_lower = q_clean.lower()

        # Retrieve relevant chunks
        retrieval_chunks = self.retrieve_context(custom_query=q_clean, top_k=8)
        grounding_refs = self.map_chunks_to_references(retrieval_chunks, max_refs=8)
        grounded_docs = sorted(list(set(r.filename for r in grounding_refs)))

        # Fallback if no documents exist in vector store
        if not retrieval_chunks:
            return ChatQueryResponse(
                conversation_id=conv_id,
                question=q_clean,
                answer=(
                    "I could not find any relevant project documents in the knowledge base. "
                    "Please upload PDF, DOCX, CSV, or TXT project artifacts using the Ingestion tab first."
                ),
                source_references=[],
                retrieved_chunks_count=0,
                grounded_document_names=[],
                suggested_followups=[
                    "What documents are currently ingested?",
                    "How do I upload new project files?"
                ],
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

        # -------------------------------------------------------------
        # Intent 1: "Are we on track?" / Schedule Status / Health Check
        # -------------------------------------------------------------
        if any(p in q_lower for p in ["on track", "project health", "schedule status", "are we delayed", "delivery status"]):
            health_res = self.health_scorer.compute_health(retrieval_chunks=retrieval_chunks)
            scope_res = self.scope_agent.analyze(retrieval_chunks=retrieval_chunks)
            risk_res = self.risk_agent.analyze(retrieval_chunks=retrieval_chunks)
            blocker_res = self.blocker_agent.analyze(retrieval_chunks=retrieval_chunks)

            status_badge = f"**{health_res.health_status.upper()}** (Score: {health_res.overall_health_score}/100)"
            
            all_risks = getattr(risk_res, "detected_risks", None) or getattr(risk_res, "identified_risks", [])

            lines = [
                f"### 🚦 Overall Project Status: {status_badge}\n",
                f"Based on the analysis of uploaded artifacts (*{', '.join(grounded_docs)}*), here is the current delivery assessment:\n",
                f"- **Scope Clarity**: `{health_res.scope_clarity_score}/100` — {len(scope_res.project_goals)} goal(s) and {len(scope_res.deliverables)} deliverable(s) defined.",
                f"- **Timeline Feasibility**: `{health_res.timeline_risk_score}/100` — {len(all_risks)} active risk(s) monitored.",
                f"- **Blocker Severity**: `{health_res.blocker_score}/100` — {len(blocker_res.active_blockers)} active blocker(s) identified.\n"
            ]

            if blocker_res.active_blockers:
                lines.append("#### 🛑 Active Blockers Affecting Track:")
                for b in blocker_res.active_blockers[:3]:
                    lines.append(f"- **{b.description}** (Category: {b.category}, Owner: {b.owner})")
                lines.append("")

            if all_risks:
                lines.append("#### ⚠️ Key Schedule & Delivery Risks:")
                for r in all_risks[:2]:
                    r_sev = getattr(r, "level", None) or getattr(r, "severity", "Medium")
                    r_reason = getattr(r, "reason", None) or getattr(r, "rationale", "")
                    lines.append(f"- **{r.title}** ({r_sev}): {r_reason}")
                lines.append("")

            if health_res.recommendations:
                lines.append("#### 💡 Next Recommended Action:")
                top_rec = health_res.recommendations[0]
                lines.append(f"- {top_rec.action} (Target: {top_rec.target_owner})")

            answer = "\n".join(lines)
            followups = [
                "What are our biggest risks?",
                "What are the current blockers?",
                "What are the pending action items?"
            ]

        # -------------------------------------------------------------
        # Intent 2: "What are our biggest risks?" / Risks Analysis
        # -------------------------------------------------------------
        elif any(p in q_lower for p in ["risk", "biggest risk", "key risk", "what are our risks", "risk register", "risks identified"]):
            risk_res = self.risk_agent.analyze(retrieval_chunks=retrieval_chunks)
            all_risks = getattr(risk_res, "detected_risks", None) or getattr(risk_res, "identified_risks", [])

            if not all_risks:
                answer = "No significant project risks were identified from the currently uploaded project documents."
            else:
                lines = [
                    f"### ⚠️ Identified Project Risks ({len(all_risks)})\n",
                    f"Here are the top project risks identified from `{', '.join(grounded_docs)}`:\n"
                ]
                for i, r in enumerate(all_risks, 1):
                    sev_str = str(getattr(r, "level", None) or getattr(r, "severity", "Medium"))
                    reason_str = getattr(r, "reason", None) or getattr(r, "rationale", "")
                    mitigation = getattr(r, "suggested_mitigation", None) or getattr(r, "mitigation_recommendation", None)
                    src_doc = getattr(r, "source_document", "Uploaded Documentation")
                    lines.append(f"**{i}. {r.title}** — `Severity: {sev_str}` | `Category: {getattr(r, 'category', 'Risk')}`")
                    lines.append(f"- **Details**: {reason_str}")
                    if mitigation:
                        lines.append(f"- **Mitigation**: {mitigation}")
                    lines.append(f"- *Source*: `{src_doc}`\n")

                forecast_summary = getattr(getattr(risk_res, "delivery_forecast", None), "projected_delay_summary", None) or getattr(risk_res, "summary", "Delivery schedule active.")
                lines.append(f"**Delivery Forecast**: {forecast_summary}")
                answer = "\n".join(lines)

            followups = [
                "Are we on track?",
                "What are the current blockers?",
                "Generate a full risk register"
            ]

        # -------------------------------------------------------------
        # Intent 3: "What are the current blockers?" / Blockers
        # -------------------------------------------------------------
        elif any(p in q_lower for p in ["blocker", "blocking", "what is blocking", "unresolved issues", "dependencies"]):
            blocker_res = self.blocker_agent.analyze(retrieval_chunks=retrieval_chunks)

            if not blocker_res.active_blockers:
                answer = (
                    f"### 🛑 Active Blockers (0)\n\n"
                    f"No active blockers were identified from the uploaded project documents. "
                    f"However, there are **{len(blocker_res.action_items)} action items** and "
                    f"**{len(blocker_res.pending_decisions)} pending decisions** being tracked."
                )
            else:
                lines = [
                    f"### 🛑 Active Blockers ({len(blocker_res.active_blockers)})\n",
                    f"The following active blockers were extracted from `{', '.join(grounded_docs)}`:\n"
                ]
                for i, b in enumerate(blocker_res.active_blockers, 1):
                    lines.append(f"**{i}. {b.description}** — `Severity: {b.severity}` | `Category: {b.category}`")
                    if b.related_dependency:
                        lines.append(f"- **Dependency**: {b.related_dependency}")
                    if b.owner and b.owner != "Unassigned":
                        lines.append(f"- **Owner**: {b.owner}")
                    lines.append(f"- *Source*: `{b.source_document}`\n")

                answer = "\n".join(lines)

            followups = [
                "What are the pending action items?",
                "Are we on track?",
                "What are our biggest risks?"
            ]

        # -------------------------------------------------------------
        # Intent 4: "What are the pending action items?" / Actions
        # -------------------------------------------------------------
        elif any(p in q_lower for p in ["action item", "pending action", "tasks", "what needs to be done", "next steps"]):
            blocker_res = self.blocker_agent.analyze(retrieval_chunks=retrieval_chunks)

            if not blocker_res.action_items:
                answer = "No explicit pending action items were identified in the uploaded project documents."
            else:
                lines = [
                    f"### ✅ Pending Action Items & Next Steps ({len(blocker_res.action_items)})\n",
                    f"Extracted from `{', '.join(grounded_docs)}`:\n"
                ]
                for i, a in enumerate(blocker_res.action_items, 1):
                    due = f" | Due: {a.due_date}" if a.due_date else ""
                    lines.append(f"- **{a.task_description}** (Assignee: `{a.assignee}`{due}) — Status: `{a.status}`")
                
                answer = "\n".join(lines)

            followups = [
                "What are the current blockers?",
                "What are the project deliverables?",
                "Are we on track?"
            ]

        # -------------------------------------------------------------
        # Intent 5: "What are the project deliverables?" / Scope & Goals
        # -------------------------------------------------------------
        elif any(p in q_lower for p in ["deliverable", "project scope", "project goals", "objectives", "milestone"]):
            scope_res = self.scope_agent.analyze(retrieval_chunks=retrieval_chunks)

            lines = [f"### 🎯 Project Scope & Deliverables\n"]
            if scope_res.project_title:
                lines.append(f"**Project**: {scope_res.project_title}\n")

            if scope_res.project_goals:
                lines.append("#### Project Goals:")
                for g in scope_res.project_goals:
                    lines.append(f"- {g.statement} (*{g.category.title()}*)")
                lines.append("")

            if scope_res.deliverables:
                lines.append(f"#### Key Deliverables ({len(scope_res.deliverables)}):")
                for d in scope_res.deliverables:
                    due = f" (Due: {d.target_date})" if d.target_date else ""
                    lines.append(f"- **{d.name}** — Owner: `{d.owner}` | Status: `{d.status}`{due}")
                lines.append("")

            if scope_res.milestones:
                lines.append("#### Milestones:")
                for m in scope_res.milestones:
                    target = f" -> Target: {m.target_timeline}" if m.target_timeline else ""
                    lines.append(f"- **{m.title}**{target}")

            answer = "\n".join(lines) if len(lines) > 2 else "No explicit deliverables or goals found in the documents."
            followups = [
                "Are we on track?",
                "Generate user stories from deliverables",
                "What are our biggest risks?"
            ]

        # -------------------------------------------------------------
        # Intent 6: Ad-Hoc / Custom Semantic Q&A
        # -------------------------------------------------------------
        else:
            # Check relevance & grounding
            stop_words = {
                "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
                "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
                "do", "does", "did", "can", "could", "should", "would", "will", "shall",
                "may", "might", "must", "the", "a", "an", "and", "or", "but", "if", "then",
                "in", "on", "at", "to", "for", "with", "by", "from", "about", "as", "into",
                "through", "during", "before", "after", "above", "below", "up", "down", "out",
                "off", "over", "under", "again", "further", "then", "once", "here", "there",
                "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
                "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "using",
                "project", "document", "documents", "tell", "show", "give", "please"
            }
            query_terms = [w.strip("?,.!;:\'\"()[]{}") for w in q_lower.split() if len(w) >= 3]
            sig_terms = [w for w in query_terms if w not in stop_words and len(w) >= 3]

            all_retrieved_text = " ".join(c.content.lower() for c in retrieval_chunks)
            has_term_overlap = any(term in all_retrieved_text for term in sig_terms) if sig_terms else True
            max_score = max(c.score for c in retrieval_chunks) if retrieval_chunks else 0.0

            # Grounding validation threshold
            if (sig_terms and not has_term_overlap) or max_score < 0.20:
                answer = (
                    f"The uploaded project documents do not appear to contain sufficient information "
                    f"to answer: *\"{q_clean}\"*.\n\n"
                    f"Currently indexed documents in the workspace: **{', '.join(grounded_docs) if grounded_docs else 'None'}**.\n"
                    f"Please upload relevant files or try rephrasing your question."
                )
                followups = [
                    "Are we on track?",
                    "What are our biggest risks?",
                    "What are the project deliverables?"
                ]
            else:
                lines = [
                    f"Based on the project documentation (*{', '.join(grounded_docs)}*):\n"
                ]
                # Synthesize relevant excerpts
                for i, c in enumerate(retrieval_chunks[:3], 1):
                    content_clean = c.content.strip()
                    loc = f"Page {c.metadata.page_number}" if c.metadata.page_number else f"Row {c.metadata.row_number}" if c.metadata.row_number else f"Section: {c.metadata.section_title or 'General'}"
                    lines.append(f"**From `{c.metadata.filename}` ({loc})**:")
                    lines.append(f"> {content_clean}\n")

                lines.append(
                    f"**Summary**: The indexed artifacts reference this topic directly in `{', '.join(grounded_docs)}`. "
                    f"Please refer to the source references below for full provenance."
                )
                answer = "\n".join(lines)
                followups = [
                    "What are the active blockers?",
                    "What are the project deliverables?",
                    "What is our overall health score?"
                ]

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ChatQueryResponse(
            conversation_id=conv_id,
            question=q_clean,
            answer=answer,
            source_references=grounding_refs,
            retrieved_chunks_count=len(retrieval_chunks),
            grounded_document_names=grounded_docs,
            suggested_followups=followups,
            execution_time_ms=elapsed_ms
        )

    def analyze(
        self,
        retrieval_chunks: Optional[List[RetrievedChunk]] = None,
        query_context: Optional[str] = None
    ) -> BaseAgentResult:
        """Standard BaseAgent analyze wrapper."""
        question = query_context or "What is the overall project status?"
        res = self.answer_question(question=question)
        return BaseAgentResult(
            agent_name=self.name,
            agent_role=self.role,
            execution_status=AgentExecutionStatus.SUCCESS,
            retrieved_chunks_count=res.retrieved_chunks_count,
            grounding_references=res.source_references,
            execution_time_ms=res.execution_time_ms,
            notes=res.answer
        )
