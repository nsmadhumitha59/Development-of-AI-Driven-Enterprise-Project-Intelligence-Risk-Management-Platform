from typing import List
from app.schemas import AgentSpec, ArchitectureInfo
from app.config import settings

MULTI_AGENT_SPECS: List[AgentSpec] = [
    AgentSpec(
        name="Document Ingestion & RAG Agent",
        milestone="Milestone 1 (Implemented)",
        status="Active",
        responsibilities=[
            "Extract raw content from PDF, DOCX, CSV, and TXT files",
            "Normalize text whitespace, control characters, and line breaks",
            "Extract and persist file metadata (checksum, size, character & word counts)",
            "Perform recursive character text chunking with overlap",
            "Generate 384-dim dense vector embeddings using SentenceTransformers",
            "Index chunk vectors and metadata in persistent local ChromaDB",
            "Execute semantic similarity retrieval queries across indexed project data"
        ],
        inputs=["Uploaded Document Files (.pdf, .docx, .csv, .txt)", "Semantic Search Queries"],
        outputs=["Extracted Text Chunks", "Document Metadata Records", "Vector Search Hits with Similarity Scores"]
    ),
    AgentSpec(
        name="Risk Advisor Agent",
        milestone="Milestone 2 (Future Scope)",
        status="Planned",
        responsibilities=[
            "Analyze retrieved project document chunks for technical, operational, and financial risks",
            "Assign severity scores (High, Medium, Low) based on risk impact",
            "Generate actionable risk mitigation recommendations"
        ],
        inputs=["Semantic Context Chunks", "Project Deliverables & Requirements"],
        outputs=["Structured Risk Assessment Report", "Severity Breakdown"]
    ),
    AgentSpec(
        name="Delivery Forecast Agent",
        milestone="Milestone 3 (Future Scope)",
        status="Planned",
        responsibilities=[
            "Analyze sprint CSV data, velocity metrics, and requirement timelines",
            "Forecast completion dates and identify sprint bottlenecks"
        ],
        inputs=["CSV Sprint Data", "Project Milestone Requirements"],
        outputs=["Estimated Delivery Dates", "Velocity Variance Analysis"]
    ),
    AgentSpec(
        name="Blocker & Action Item Agent",
        milestone="Milestone 4 (Future Scope)",
        status="Planned",
        responsibilities=[
            "Identify active impediments and unresolved blockers from meeting notes & DOCX specs",
            "Extract action items with assigned owners and target resolution dates"
        ],
        inputs=["Meeting Minutes (TXT)", "Status Reports (PDF/DOCX)"],
        outputs=["List of Open Blockers", "Action Item Tracker"]
    ),
    AgentSpec(
        name="Conversational Intelligence Assistant Agent",
        milestone="Milestone 5 (Future Scope)",
        status="Planned",
        responsibilities=[
            "Synthesize RAG retrieval results and multi-agent outputs into natural conversational answers",
            "Provide interactive Q&A over indexed project knowledge base"
        ],
        inputs=["User Natural Language Prompt", "Multi-Agent Intelligence Context"],
        outputs=["Conversational Answer with Source Citations"]
    )
]

def get_system_architecture_info() -> ArchitectureInfo:
    """Returns system architecture specs and multi-agent structure."""
    return ArchitectureInfo(
        system_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        rag_pipeline={
            "ingestion_formats": ["PDF", "DOCX", "CSV", "TXT"],
            "normalization": "Whitespace, line-ending & control char removal",
            "chunking_strategy": f"Recursive Character Chunker (size={settings.CHUNK_SIZE}, overlap={settings.CHUNK_OVERLAP})",
            "embedding_model": settings.EMBEDDING_MODEL_NAME,
            "embedding_dimensions": 384,
            "vector_database": "ChromaDB (Local Persistent Vector DB)",
            "distance_metric": "Cosine Similarity"
        },
        multi_agent_framework=MULTI_AGENT_SPECS
    )
