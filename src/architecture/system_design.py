"""
System Architecture & Agent Blueprint Definitions for AI Project Intelligence & Risk Advisor.

This module provides formal definitions and blueprints for:
1. Overall System Architecture
2. End-to-End RAG Pipeline Flow
3. Multi-Agent System Structure and Responsibilities
4. Future Milestone Extensibility Interfaces
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# =====================================================================
# 1. Multi-Agent System Roles & Definitions (Design Blueprints)
# =====================================================================

class AgentRole(str, Enum):
    """Enumeration of agent roles in the AI Project Intelligence system."""
    ORCHESTRATOR = "orchestrator"
    INGESTION_AGENT = "ingestion_agent"
    RISK_DETECTION_AGENT = "risk_detection_agent"
    DELIVERY_FORECAST_AGENT = "delivery_forecast_agent"
    BLOCKER_ACTION_AGENT = "blocker_action_agent"
    DOCS_GENERATION_AGENT = "docs_generation_agent"
    PROJECT_HEALTH_AGENT = "project_health_agent"
    CONVERSATIONAL_ADVISOR = "conversational_advisor"


class AgentStatus(str, Enum):
    """Operational status of agents in the multi-agent network."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentMetadata:
    """Agent definition and capability description."""
    role: AgentRole
    name: str
    description: str
    milestone: int
    inputs: List[str]
    outputs: List[str]
    dependencies: List[AgentRole] = field(default_factory=list)


# Formal registry of all system agents across milestones
SYSTEM_AGENT_REGISTRY: Dict[AgentRole, AgentMetadata] = {
    AgentRole.INGESTION_AGENT: AgentMetadata(
        role=AgentRole.INGESTION_AGENT,
        name="Document Ingestion & Context Indexer",
        description="Extracts, normalizes, chunks, embeds, and indexes project artifacts (PDF, DOCX, CSV, TXT) into vector storage.",
        milestone=1,
        inputs=["Raw project artifacts, meeting notes, sprint sheets, PRDs, task exports"],
        outputs=["Normalized text chunks", "Document metadata", "Vector embeddings in ChromaDB"],
        dependencies=[]
    ),
    AgentRole.ORCHESTRATOR: AgentMetadata(
        role=AgentRole.ORCHESTRATOR,
        name="Master Project Supervisor & Workflow Router",
        description="Coordinates multi-agent execution graphs, routes queries, aggregates insights, and synthesizes overall reports.",
        milestone=2,
        inputs=["User query / triggered schedule", "RAG retrieval contexts"],
        outputs=["Multi-agent execution plan", "Consolidated project intelligence report"],
        dependencies=[AgentRole.INGESTION_AGENT]
    ),
    AgentRole.RISK_DETECTION_AGENT: AgentMetadata(
        role=AgentRole.RISK_DETECTION_AGENT,
        name="Risk Identification & Impact Analyzer",
        description="Analyzes project chunks and status reports to detect timeline, technical, resource, and scope risks with severity scoring.",
        milestone=2,
        inputs=["RAG retrieved contexts", "Historical project patterns"],
        outputs=["Structured risk log", "Severity/probability matrix", "Mitigation suggestions"],
        dependencies=[AgentRole.INGESTION_AGENT]
    ),
    AgentRole.DELIVERY_FORECAST_AGENT: AgentMetadata(
        role=AgentRole.DELIVERY_FORECAST_AGENT,
        name="Delivery Forecasting & Velocity Advisor",
        description="Evaluates sprint velocity, ticket completion rates, and milestones to forecast delivery dates and slippage probability.",
        milestone=2,
        inputs=["Task CSV data", "Sprint summaries", "PRD timelines"],
        outputs=["Completion date forecast", "Confidence interval", "Velocity trends"],
        dependencies=[AgentRole.INGESTION_AGENT]
    ),
    AgentRole.BLOCKER_ACTION_AGENT: AgentMetadata(
        role=AgentRole.BLOCKER_ACTION_AGENT,
        name="Blocker Resolution & Action Item Extractor",
        description="Parses meeting notes, issue discussions, and sprint logs to identify active blockers, owners, and concrete next actions.",
        milestone=2,
        inputs=["Meeting notes (DOCX/TXT)", "Daily standup logs"],
        outputs=["Action item list", "Assigned owners", "Blocker escalation list"],
        dependencies=[AgentRole.INGESTION_AGENT]
    ),
    AgentRole.PROJECT_HEALTH_AGENT: AgentMetadata(
        role=AgentRole.PROJECT_HEALTH_AGENT,
        name="Project Health & Scorecard Evaluator",
        description="Computes composite project health scores across schedule, quality, risk, and team bandwidth dimensions.",
        milestone=3,
        inputs=["Risk outputs", "Delivery forecast", "Blocker statuses"],
        outputs=["Overall health index (0-100)", "Dimension breakdown", "Executive summary"],
        dependencies=[AgentRole.RISK_DETECTION_AGENT, AgentRole.DELIVERY_FORECAST_AGENT]
    ),
    AgentRole.DOCS_GENERATION_AGENT: AgentMetadata(
        role=AgentRole.DOCS_GENERATION_AGENT,
        name="Automated Documentation & Report Generator",
        description="Generates executive briefing memos, weekly stakeholder status reports, and technical summaries from retrieved intelligence.",
        milestone=3,
        inputs=["Synthesized agent outputs", "Document knowledge base"],
        outputs=["Markdown/PDF executive report", "Release notes", "Sprint retrospectives"],
        dependencies=[AgentRole.ORCHESTRATOR]
    ),
    AgentRole.CONVERSATIONAL_ADVISOR: AgentMetadata(
        role=AgentRole.CONVERSATIONAL_ADVISOR,
        name="Conversational Project Intelligence Assistant",
        description="Interactive Q&A assistant answering questions about project timelines, technical decisions, blockers, and recommendations with citations.",
        milestone=3,
        inputs=["User natural language prompt", "RAG semantic search results"],
        outputs=["Streaming contextual answers", "Document citations", "Follow-up recommendations"],
        dependencies=[AgentRole.INGESTION_AGENT]
    )
}


# =====================================================================
# 2. Shared State Contracts & RAG Context Structures
# =====================================================================

class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    CSV = "csv"
    TXT = "txt"


class ChunkMetadata(BaseModel):
    """Metadata schema attached to every indexed vector chunk."""
    document_id: str
    filename: str
    file_type: DocumentType
    chunk_index: int
    start_char: int
    end_char: int
    page_number: Optional[int] = None
    row_number: Optional[int] = None
    section_title: Optional[str] = None
    timestamp: str
    token_estimate: int


class RetrievedChunk(BaseModel):
    """Standardized retrieval object returned by the RAG pipeline."""
    chunk_id: str
    content: str
    metadata: ChunkMetadata
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")


class MultiAgentProjectState(BaseModel):
    """
    Unified state schema that flows across agents in the multi-agent graph.
    Milestone 1 establishes the baseline retrieval_context.
    """
    project_id: str = "default_project"
    session_id: str
    query: Optional[str] = None
    retrieval_context: List[RetrievedChunk] = Field(default_factory=list)
    agent_outputs: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


def get_architecture_overview() -> Dict[str, Any]:
    """Returns a structured dictionary of the overall system architecture."""
    return {
        "system_name": "AI Project Intelligence & Risk Advisor",
        "current_milestone": 1,
        "milestone_1_components": {
            "document_ingestion": [
                "PDF Parser (pypdf text & layout extractor)",
                "DOCX Parser (python-docx paragraph & table extractor)",
                "CSV Parser (pandas tabular and row-wise text builder)",
                "TXT Parser (multi-encoding robust reader)",
                "Content Normalizer (whitespace, unicode, control character cleanup)",
                "Document Registry & Metadata Store"
            ],
            "rag_pipeline": [
                "Recursive Structure-Aware Text Splitter with sliding window overlap",
                "SentenceTransformers Local Embeddings (all-MiniLM-L6-v2, 384 dim)",
                "Local Vector Storage (ChromaDB persistent collection)",
                "Semantic Retriever with cosine similarity scoring, top-k filtering, and metadata constraints"
            ],
            "api_and_ui": [
                "FastAPI REST API with asynchronous file upload and querying endpoints",
                "Interactive Web Test Dashboard for uploading, inspection, and semantic search"
            ],
            "testing_suite": [
                "Pytest suite covering all parsers, chunking, embeddings, vectorstore, and semantic retrieval"
            ]
        },
        "agents": {role.value: meta.__dict__ for role, meta in SYSTEM_AGENT_REGISTRY.items()}
    }
