"""
Tests for Milestone 3 Conversational Project Intelligence Assistant.
"""
import pytest
from src.rag.retriever import SemanticRetriever
from src.ingestion.parsers.docx_parser import DOCXParser
from src.ingestion.parsers.csv_parser import CSVParser
from src.ingestion.parsers.txt_parser import TXTParser
from src.agents.chat_assistant import ProjectIntelligenceChatAssistant, ChatQueryResponse


class TestChatAssistant:

    @pytest.fixture(autouse=True)
    def setup_documents(
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

        self.retriever = retriever
        self.assistant = ProjectIntelligenceChatAssistant(retriever=retriever)

    def test_query_are_we_on_track(self):
        res = self.assistant.answer_question("Are we on track?")
        assert isinstance(res, ChatQueryResponse)
        assert len(res.answer) > 20
        assert len(res.source_references) > 0
        assert len(res.suggested_followups) > 0

    def test_query_biggest_risks(self):
        res = self.assistant.answer_question("What are our biggest risks?")
        assert isinstance(res, ChatQueryResponse)
        assert len(res.answer) > 20
        assert len(res.source_references) > 0

    def test_query_current_blockers(self):
        res = self.assistant.answer_question("What are the current blockers?")
        assert isinstance(res, ChatQueryResponse)
        assert len(res.answer) > 20
        assert len(res.source_references) > 0

    def test_query_pending_action_items(self):
        res = self.assistant.answer_question("What are the pending action items?")
        assert isinstance(res, ChatQueryResponse)
        assert len(res.answer) > 20
        assert len(res.source_references) > 0

    def test_query_project_deliverables(self):
        res = self.assistant.answer_question("What are the project deliverables?")
        assert isinstance(res, ChatQueryResponse)
        assert len(res.answer) > 20
        assert len(res.source_references) > 0

    def test_guardrail_unsupported_question(self):
        res = self.assistant.answer_question("How do I launch a spaceship to Mars using rocket fuel X?")
        assert isinstance(res, ChatQueryResponse)
        assert "do not appear to contain sufficient information" in res.answer or "not contain" in res.answer
