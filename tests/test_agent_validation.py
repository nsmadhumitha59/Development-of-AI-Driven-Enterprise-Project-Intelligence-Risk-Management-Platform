"""
Validation test suite for Milestone 2 agents across PDF, DOCX, CSV, and TXT formats.
Tests varied phrasing extraction, active blocker vs action item separation, and empty states.
"""
import pytest
from pathlib import Path
from src.ingestion.parsers import PDFParser, DOCXParser, CSVParser, TXTParser
from src.agents import (
    ScopeExtractionAgent,
    RiskForecastAgent,
    BlockerActionAgent,
    Milestone2MultiAgentPipeline
)


class TestAgentMultiFormatValidation:
    def test_pipeline_across_all_four_document_types(
        self,
        test_vector_store,
        embedding_service,
        sample_pdf_file,
        sample_docx_file,
        sample_csv_file,
        sample_txt_file
    ):
        test_vector_store.reset()
        from src.rag.retriever import SemanticRetriever
        retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)

        # 1. Ingest all 4 formats into RAG knowledge base
        parsed_pdf = PDFParser().parse(sample_pdf_file)
        parsed_docx = DOCXParser().parse(sample_docx_file)
        parsed_csv = CSVParser().parse(sample_csv_file)
        parsed_txt = TXTParser().parse(sample_txt_file)

        chunks_pdf = retriever.index_document(parsed_pdf)
        chunks_docx = retriever.index_document(parsed_docx)
        chunks_csv = retriever.index_document(parsed_csv)
        chunks_txt = retriever.index_document(parsed_txt)

        assert len(chunks_pdf) > 0
        assert len(chunks_docx) > 0
        assert len(chunks_csv) > 0
        assert len(chunks_txt) > 0

        # 2. Run multi-agent pipeline
        pipeline = Milestone2MultiAgentPipeline(retriever=retriever)
        analysis_report = pipeline.run_all()

        assert analysis_report.success is True
        assert analysis_report.total_execution_time_ms > 0

        # 3. Validate Scope Agent outputs are grounded
        assert len(analysis_report.scope_analysis.goals) > 0
        assert len(analysis_report.scope_analysis.deliverables) > 0
        for d in analysis_report.scope_analysis.deliverables:
            if d.source_reference:
                assert d.source_reference.chunk_id is not None
                assert d.source_reference.filename in [
                    sample_pdf_file.name,
                    sample_docx_file.name,
                    sample_csv_file.name,
                    sample_txt_file.name
                ]

        # 4. Validate Risk & Forecast Agent outputs
        assert analysis_report.risk_and_forecast.forecast is not None
        assert analysis_report.risk_and_forecast.total_risks_detected > 0

        # 5. Validate Blocker & Action Agent outputs
        assert len(analysis_report.blockers_and_actions.action_items) > 0
        for act in analysis_report.blockers_and_actions.action_items:
            if act.source_reference:
                assert act.source_reference.chunk_id is not None

        # 6. Validate executive summary is synthesized
        assert len(analysis_report.overall_executive_summary) > 20

    def test_varied_goal_wording_extraction(self, test_vector_store, embedding_service, temp_test_dir):
        """Tests that Scope Agent recognizes diverse goal phrasing without exact 'Project Goals' heading."""
        test_vector_store.reset()
        from src.rag.retriever import SemanticRetriever
        retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)

        file_path = temp_test_dir / "custom_project_manifest.txt"
        content = (
            "System Initiative Overview\n\n"
            "The primary aim is to automate release compliance checks and reduce deployment errors.\n"
            "Business Objective: Accelerate time-to-market for enterprise microservices.\n"
            "The project intends to streamline cross-team communications across quarterly releases.\n"
            "Expected outcome is 99.9% uptime for payment gateways."
        )
        file_path.write_text(content, encoding="utf-8")
        parsed = TXTParser().parse(file_path)
        retriever.index_document(parsed)

        agent = ScopeExtractionAgent(retriever=retriever)
        result = agent.analyze()

        assert len(result.project_goals) >= 3
        statements = [g.statement.lower() for g in result.project_goals]
        assert any("automate release compliance" in s or "deployment errors" in s for s in statements)
        assert any("time-to-market" in s for s in statements)
        for g in result.project_goals:
            assert g.goal_id.startswith("GOL-")
            assert g.supporting_context is not None
            assert g.source_document == file_path.name
            assert g.source_reference is not None

    def test_active_blocker_vs_action_item_separation(self, test_vector_store, embedding_service, temp_test_dir):
        """Verifies clear separation between active blockers and action items."""
        test_vector_store.reset()
        from src.rag.retriever import SemanticRetriever
        retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)

        file_path = temp_test_dir / "daily_standup_status.txt"
        content = (
            "Daily Engineering Standup Notes\n\n"
            "Blockers:\n"
            "- Maintenance is waiting for a replacement part from the supplier.\n"
            "- Backup indoor venue approval is pending from city council.\n\n"
            "Action Items:\n"
            "- Coordinator: confirm catering delivery time by 3 PM.\n"
            "- Volunteer lead: recruit 8 volunteers for the weekend shift.\n"
            "- Operations supervisor will arrange forklift inspection."
        )
        file_path.write_text(content, encoding="utf-8")
        parsed = TXTParser().parse(file_path)
        retriever.index_document(parsed)

        agent = BlockerActionAgent(retriever=retriever)
        result = agent.analyze()

        # Check Active Blockers
        assert len(result.active_blockers) >= 2
        blocker_descs = [b.description.lower() for b in result.active_blockers]
        assert any("replacement part" in b or "waiting for" in b for b in blocker_descs)
        assert any("indoor venue" in b or "pending" in b for b in blocker_descs)

        # Check Action Items (Not classified as blockers)
        assert len(result.action_items) >= 2
        action_descs = [a.task_description.lower() for a in result.action_items]
        assert any("catering delivery" in a for a in action_descs)
        assert any("recruit" in a for a in action_descs)

        # Ensure action items are not in blockers list
        for act in result.action_items:
            assert not any(act.task_description == b.description for b in result.active_blockers)

    def test_empty_blocker_state_message(self, test_vector_store, embedding_service, temp_test_dir):
        """Verifies meaningful message when no active blockers exist."""
        test_vector_store.reset()
        from src.rag.retriever import SemanticRetriever
        retriever = SemanticRetriever(vector_store=test_vector_store, embedding_service=embedding_service)

        file_path = temp_test_dir / "smooth_sprint_notes.txt"
        content = (
            "Sprint Progress Notes\n\n"
            "Action Items:\n"
            "- Engineer Alice: complete code review for API models.\n"
            "- Engineer Bob: update integration test coverage."
        )
        file_path.write_text(content, encoding="utf-8")
        parsed = TXTParser().parse(file_path)
        retriever.index_document(parsed)

        agent = BlockerActionAgent(retriever=retriever)
        result = agent.analyze()

        assert len(result.active_blockers) == 0
        assert result.empty_blockers_message == "No active blockers identified from the uploaded documents."
        assert "No active blockers identified" in result.executive_summary
        assert "action items identified" in result.executive_summary
        assert len(result.action_items) >= 2
