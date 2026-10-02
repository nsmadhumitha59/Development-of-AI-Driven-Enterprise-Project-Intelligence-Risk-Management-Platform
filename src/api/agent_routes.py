"""
FastAPI Routes for Milestone 2 Multi-Agent Intelligence Services.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.agents import (
    ScopeExtractionAgent,
    ScopeExtractionResult,
    RiskForecastAgent,
    RiskForecastResult,
    BlockerActionAgent,
    BlockerActionResult,
    Milestone2MultiAgentPipeline,
    Milestone2AnalysisResult
)
from src.rag.retriever import SemanticRetriever
from src.rag.embeddings import EmbeddingService
from src.rag.vectorstore import ChromaVectorStore

router = APIRouter(prefix="/api/v1/agents", tags=["Milestone 2 - Specialized Agents"])

# Shared pipeline instances
retriever = SemanticRetriever(
    vector_store=ChromaVectorStore(),
    embedding_service=EmbeddingService.get_instance()
)
scope_agent = ScopeExtractionAgent(retriever=retriever)
risk_agent = RiskForecastAgent(retriever=retriever)
blocker_agent = BlockerActionAgent(retriever=retriever)
pipeline = Milestone2MultiAgentPipeline(retriever=retriever)


class AgentExecutionRequest(BaseModel):
    query_context: Optional[str] = Field(
        default=None,
        description="Optional guiding search context or focus question (e.g. 'Payment gateway release sprint')"
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Optional filter to restrict agent analysis to a single document"
    )


@router.post(
    "/scope",
    response_model=ScopeExtractionResult,
    summary="Run Scope & Deliverable Extraction Agent",
    description="Retrieves from RAG knowledge base and extracts project goals, scope boundaries, deliverables, milestones, and owner assignments."
)
async def run_scope_agent(request: Optional[AgentExecutionRequest] = None):
    try:
        custom_query = request.query_context if request else None
        chunks = None
        if request and request.document_id:
            chunks = retriever.retrieve(query="project goals scope deliverables", document_id=request.document_id, top_k=10)
        
        result = scope_agent.analyze(retrieval_chunks=chunks, query_context=custom_query)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scope Extraction Agent failed: {str(e)}"
        )


@router.post(
    "/risk-forecast",
    response_model=RiskForecastResult,
    summary="Run Risk Detection & Delivery Forecasting Agent",
    description="Detects schedule risks, dependency gaps, missing requirements, delivery challenges, and computes grounded delivery forecast."
)
async def run_risk_forecast_agent(request: Optional[AgentExecutionRequest] = None):
    try:
        custom_query = request.query_context if request else None
        chunks = None
        if request and request.document_id:
            chunks = retriever.retrieve(query="risks bottlenecks blockers delays dependencies", document_id=request.document_id, top_k=10)

        result = risk_agent.analyze(retrieval_chunks=chunks, query_context=custom_query)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk & Delivery Forecast Agent failed: {str(e)}"
        )


@router.post(
    "/blockers-actions",
    response_model=BlockerActionResult,
    summary="Run Blocker & Action Item Identification Agent",
    description="Identifies active blockers, pending decisions, unresolved issues, and action items with assignees and due dates."
)
async def run_blocker_action_agent(request: Optional[AgentExecutionRequest] = None):
    try:
        custom_query = request.query_context if request else None
        chunks = None
        if request and request.document_id:
            chunks = retriever.retrieve(query="action items blockers tasks decisions unresolved", document_id=request.document_id, top_k=10)

        result = blocker_agent.analyze(retrieval_chunks=chunks, query_context=custom_query)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Blocker & Action Item Agent failed: {str(e)}"
        )


@router.post(
    "/analyze-all",
    response_model=Milestone2AnalysisResult,
    summary="Run Full Milestone 2 Multi-Agent Pipeline",
    description="Orchestrates Scope, Risk/Forecast, and Blocker/Action agents across the knowledge base to generate comprehensive structured intelligence."
)
async def run_all_agents(request: Optional[AgentExecutionRequest] = None):
    try:
        custom_query = request.query_context if request else None
        result = pipeline.run_all(focus_query=custom_query)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Milestone 2 Multi-Agent Pipeline failed: {str(e)}"
        )
