"""
Unit and integration tests for Blocker and Action Item Identification Agent (Milestone 2 - Requirement 3).
"""
import pytest
from pathlib import Path
from src.ingestion.parsers import TXTParser, DOCXParser
from src.rag.retriever import SemanticRetriever
from src.agents.blocker_action_agent import (
    BlockerActionAgent,
    BlockerActionResult,
    BlockerSeverity,
    ActionItemPriority
)


@pytest.fixture
def meeting_minutes_file(temp_test_dir) -> Path:
    file_path = temp_test_dir / "sprint_standup_minutes.txt"
    content = (
        "Sprint Standup Meeting Minutes\n\n"
        "Blocker: Redis cache cluster is blocked by VPC peering permissions.\n"
        "Pending Decision Needed: Architecture team must decide whether to use FAISS or ChromaDB in production. Decision required by Friday.\n"
        "Unresolved Issue: Intermittent connection timeouts observed on authentication gateway.\n"
        "Action Item: Optimize ChromaDB cosine index query latency. Assignee: Bob Jones. Due: 2026-10-15.\n"
        "Action Item: Update Swagger API models with response schemas. Assignee: Alice Smith. Due: 2026-10-18."
    )
    file_path.write_text(content, encoding="utf-8")
    return file_path


class TestBlockerActionAgent:
    def test_blocker_and_action_item_extraction(self, test_vector_store, embedding_service, meeting_minutes_file):
        test_vector_store.reset()
        retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)

        parsed = TXTParser().parse(meeting_minutes_file)
        retriever.index_document(parsed)

        agent = BlockerActionAgent(retriever=retriever)
        result = agent.analyze()

        assert isinstance(result, BlockerActionResult)
        assert result.agent_role == "blocker_action_extractor"

        # Verify Blockers
        assert result.total_blockers >= 1
        assert any("VPC peering" in b.description or "Redis" in b.description for b in result.blockers)

        # Verify Action Items with Assignees and Due Dates
        assert result.total_action_items >= 2
        assignees = [a.assignee for a in result.action_items]
        assert "Bob Jones" in assignees or "Alice Smith" in assignees
        dates = [a.due_date for a in result.action_items if a.due_date]
        assert any("2026" in d for d in dates)

        # Verify Pending Decisions
        assert result.total_pending_decisions >= 1
        assert any("ChromaDB" in d.decision_needed or "FAISS" in d.decision_needed for d in result.pending_decisions)

        # Verify Unresolved Issues
        assert result.total_unresolved_issues >= 1
