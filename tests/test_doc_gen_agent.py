"""
Tests for Milestone 3 Documentation Generation Agent.
"""
import pytest
from src.rag.retriever import SemanticRetriever
from src.ingestion.parsers.docx_parser import DOCXParser
from src.ingestion.parsers.csv_parser import CSVParser
from src.ingestion.parsers.txt_parser import TXTParser
from src.agents.doc_gen_agent import (
    DocumentationGenerationAgent,
    DocumentationGenerationResult,
    UserStory,
    RiskRegisterEntry,
    ActionItemDocumentEntry
)


class TestDocumentationGenerationAgent:

    def test_documentation_generation_end_to_end(
        self,
        test_vector_store,
        embedding_service,
        sample_docx_file,
        sample_csv_file,
        sample_txt_file
    ):
        test_vector_store.reset()
        retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)

        doc_docx = DOCXParser().parse(sample_docx_file)
        doc_csv = CSVParser().parse(sample_csv_file)
        doc_txt = TXTParser().parse(sample_txt_file)

        retriever.index_document(doc_docx)
        retriever.index_document(doc_csv)
        retriever.index_document(doc_txt)

        agent = DocumentationGenerationAgent(retriever=retriever)
        res = agent.analyze()

        assert isinstance(res, DocumentationGenerationResult)
        assert res.execution_status.value == "success"
        assert res.total_user_stories > 0
        assert res.total_risks >= 0
        assert res.total_action_items > 0

        # Verify User Stories
        first_story = res.user_stories[0]
        assert isinstance(first_story, UserStory)
        assert first_story.as_a != ""
        assert first_story.i_want != ""
        assert first_story.so_that != ""
        assert len(first_story.acceptance_criteria) > 0

        # Verify Action Items
        first_action = res.action_items[0]
        assert isinstance(first_action, ActionItemDocumentEntry)
        assert first_action.task_description != ""

        # Verify Markdown Export
        assert "# 📋 AI Project Intelligence" in res.markdown_export
        assert "## 1. 📖 Agile User Stories" in res.markdown_export
        assert "## 2. 🛡️ Enterprise Risk Register" in res.markdown_export
        assert "## 3. ✅ Action Items & Execution Checklist" in res.markdown_export
