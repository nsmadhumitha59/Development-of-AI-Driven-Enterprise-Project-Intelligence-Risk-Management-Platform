"""
FastAPI REST Routes for Milestone 3 (Documentation Generation, Health Scoring, Conversational Assistant).
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from src.agents.doc_gen_agent import (
    DocumentationGenerationAgent,
    DocumentationGenerationResult,
    UserStory,
    RiskRegisterEntry,
    ActionItemDocumentEntry
)
from src.agents.health_scorer import (
    ProjectHealthScorer,
    ProjectHealthResult
)
from src.agents.chat_assistant import (
    ProjectIntelligenceChatAssistant,
    ChatQueryRequest,
    ChatQueryResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/m3", tags=["Milestone 3 - Project Intelligence & Docs"])

# Lazy-loaded singletons
_doc_agent: Optional[DocumentationGenerationAgent] = None
_health_scorer: Optional[ProjectHealthScorer] = None
_chat_assistant: Optional[ProjectIntelligenceChatAssistant] = None


def get_doc_agent() -> DocumentationGenerationAgent:
    global _doc_agent
    if _doc_agent is None:
        _doc_agent = DocumentationGenerationAgent()
    return _doc_agent


def get_health_scorer() -> ProjectHealthScorer:
    global _health_scorer
    if _health_scorer is None:
        _health_scorer = ProjectHealthScorer()
    return _health_scorer


def get_chat_assistant() -> ProjectIntelligenceChatAssistant:
    global _chat_assistant
    if _chat_assistant is None:
        _chat_assistant = ProjectIntelligenceChatAssistant()
    return _chat_assistant


class AgentRequestPayload(BaseModel):
    query_context: Optional[str] = Field(None, description="Optional custom focus context for RAG retrieval")


# =====================================================================
# 1. Documentation Generation Endpoints
# =====================================================================

@router.post("/docs/user-stories", response_model=List[UserStory])
async def generate_user_stories(payload: Optional[AgentRequestPayload] = None):
    """Generates structured Agile User Stories from uploaded project documents."""
    try:
        agent = get_doc_agent()
        query = payload.query_context if payload else None
        chunks = agent.retrieve_context(custom_query=query)
        stories = agent.generate_user_stories(retrieval_chunks=chunks)
        return stories
    except Exception as e:
        logger.error(f"Error generating user stories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"User story generation failed: {str(e)}")


@router.post("/docs/risk-register", response_model=List[RiskRegisterEntry])
async def generate_risk_register(payload: Optional[AgentRequestPayload] = None):
    """Generates structured Enterprise Risk Register from detected risks."""
    try:
        agent = get_doc_agent()
        query = payload.query_context if payload else None
        chunks = agent.retrieve_context(custom_query=query)
        register = agent.generate_risk_register(retrieval_chunks=chunks)
        return register
    except Exception as e:
        logger.error(f"Error generating risk register: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Risk register generation failed: {str(e)}")


@router.post("/docs/action-items", response_model=List[ActionItemDocumentEntry])
async def generate_action_items(payload: Optional[AgentRequestPayload] = None):
    """Generates structured Action Item Checklist from meeting notes and tasks."""
    try:
        agent = get_doc_agent()
        query = payload.query_context if payload else None
        chunks = agent.retrieve_context(custom_query=query)
        items = agent.generate_action_items(retrieval_chunks=chunks)
        return items
    except Exception as e:
        logger.error(f"Error generating action items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Action items generation failed: {str(e)}")


@router.post("/docs/all", response_model=DocumentationGenerationResult)
async def generate_all_documentation(payload: Optional[AgentRequestPayload] = None):
    """Generates comprehensive project documentation (User Stories, Risk Register, Action Items, Markdown Export)."""
    try:
        agent = get_doc_agent()
        query = payload.query_context if payload else None
        result = agent.analyze(query_context=query)
        return result
    except Exception as e:
        logger.error(f"Error running full documentation pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Full documentation generation failed: {str(e)}")


# =====================================================================
# 2. Project Health Scoring Endpoints
# =====================================================================

@router.post("/health-score", response_model=ProjectHealthResult)
async def calculate_project_health(payload: Optional[AgentRequestPayload] = None):
    """Computes overall project health score (0-100) and dimension breakdown (Scope Clarity, Timeline Risk, Blocker Severity)."""
    try:
        scorer = get_health_scorer()
        query = payload.query_context if payload else None
        result = scorer.analyze(query_context=query)
        return result
    except Exception as e:
        logger.error(f"Error computing project health score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health scoring calculation failed: {str(e)}")


# =====================================================================
# 3. Conversational Project Intelligence Assistant Endpoints
# =====================================================================

@router.post("/chat", response_model=ChatQueryResponse)
async def chat_with_project_knowledge(request: ChatQueryRequest):
    """
    RAG-powered conversational endpoint answering natural language queries with citations.
    Answers 'Are we on track?', 'What are our biggest risks?', 'What are current blockers?', etc.
    """
    try:
        assistant = get_chat_assistant()
        response = assistant.answer_question(
            question=request.message,
            conversation_id=request.conversation_id,
            session_history=request.session_history
        )
        return response
    except Exception as e:
        logger.error(f"Error answering chat question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversational assistant error: {str(e)}")
