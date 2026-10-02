"""
Unit and integration tests for Scope and Deliverable Extraction Agent (Milestone 2 - Requirement 1).
"""
import pytest
from src.ingestion.parsers import DOCXParser, PDFParser, CSVParser, TXTParser
from src.rag.retriever import SemanticRetriever
from src.agents.scope_agent import ScopeExtractionAgent, ScopeExtractionResult


class TestScopeExtractionAgent:
    def test_scope_extraction_from_charter_and_tasks(
        self,
        test_vector_store,
        embedding_service,
        sample_docx_file,
        sample_csv_file,
        sample_txt_file
    ):
        test_vector_store.reset()
        retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)

        # Index project charter, tasks CSV, and notes TXT
        doc_docx = DOCXParser().parse(sample_docx_file)
        doc_csv = CSVParser().parse(sample_csv_file)
        doc_txt = TXTParser().parse(sample_txt_file)

        retriever.index_document(doc_docx)
        retriever.index_document(doc_csv)
        retriever.index_document(doc_txt)

        agent = ScopeExtractionAgent(retriever=retriever)
        result = agent.analyze()

        assert isinstance(result, ScopeExtractionResult)
        assert result.agent_role == "scope_extractor"
        assert result.retrieved_chunks_count > 0

        # Verify Goals
        assert len(result.goals) > 0
        assert any("minimize sprint slippage" in g.statement.lower() or "intelligence" in g.statement.lower() for g in result.goals)

        # Verify Deliverables & Assignees
        assert len(result.deliverables) > 0
        assert any(d.owner == "Alice Smith" or "Ingestion" in d.name for d in result.deliverables)

        # Verify Milestones
        assert len(result.milestones) > 0

        # Verify Grounding references
        assert len(result.grounding_references) > 0
        for ref in result.grounding_references:
            assert ref.chunk_id is not None
            assert ref.filename in [sample_docx_file.name, sample_csv_file.name, sample_txt_file.name]
            assert ref.similarity_score > 0.0

    def test_scope_extraction_empty_knowledge_base(self, test_vector_store, embedding_service):
        from src.rag.retriever import SemanticRetriever
        empty_retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)
        test_vector_store.reset()

        agent = ScopeExtractionAgent(retriever=empty_retriever)
        result = agent.analyze()
        assert result.retrieved_chunks_count == 0
        assert len(result.goals) == 0
