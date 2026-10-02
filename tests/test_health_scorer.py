"""
Tests for Milestone 3 Project Health Scoring Module.
"""
import pytest
from src.rag.retriever import SemanticRetriever
from src.ingestion.parsers.docx_parser import DOCXParser
from src.ingestion.parsers.csv_parser import CSVParser
from src.ingestion.parsers.pdf_parser import PDFParser
from src.agents.health_scorer import ProjectHealthScorer, ProjectHealthResult


class TestProjectHealthScorer:

    def test_health_scoring_calculation(
        self,
        test_vector_store,
        embedding_service,
        sample_docx_file,
        sample_csv_file,
        sample_pdf_file
    ):
        test_vector_store.reset()
        retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)

        doc_docx = DOCXParser().parse(sample_docx_file)
        doc_csv = CSVParser().parse(sample_csv_file)
        doc_pdf = PDFParser().parse(sample_pdf_file)

        retriever.index_document(doc_docx)
        retriever.index_document(doc_csv)
        retriever.index_document(doc_pdf)

        scorer = ProjectHealthScorer(retriever=retriever)
        res = scorer.analyze()

        assert isinstance(res, ProjectHealthResult)
        assert res.execution_status.value == "success"
        assert 0.0 <= res.overall_health_score <= 100.0
        assert res.health_status in ["Healthy", "At Risk", "Critical"]
        assert len(res.dimensions) == 3

        # Dimension checks
        dim_names = [d.dimension_name for d in res.dimensions]
        assert "Scope Clarity" in dim_names
        assert "Timeline Risk" in dim_names
        assert "Blocker & Issue Severity" in dim_names

        for d in res.dimensions:
            assert 0.0 <= d.score <= 100.0
            assert d.status in ["Healthy", "At Risk", "Critical"]
            assert len(d.key_factors) > 0

        # Recommendations check
        assert len(res.recommendations) > 0
        assert len(res.key_drivers) > 0
