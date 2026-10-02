"""
Integration tests for end-to-end Semantic Retrieval across ingested document types.
"""
import pytest
from src.ingestion.parsers import PDFParser, DOCXParser, CSVParser, TXTParser
from src.rag.retriever import SemanticRetriever
from src.architecture.system_design import RetrievedChunk


class TestSemanticRetrieval:
    def test_end_to_end_indexing_and_retrieval(
        self,
        semantic_retriever,
        sample_txt_file,
        sample_csv_file,
        sample_docx_file,
        sample_pdf_file
    ):
        # 1. Parse all 4 file types
        parsed_txt = TXTParser().parse(sample_txt_file)
        parsed_csv = CSVParser().parse(sample_csv_file)
        parsed_docx = DOCXParser().parse(sample_docx_file)
        parsed_pdf = PDFParser().parse(sample_pdf_file)

        # 2. Index all 4 into vector store
        chunks_txt = semantic_retriever.index_document(parsed_txt)
        chunks_csv = semantic_retriever.index_document(parsed_csv)
        chunks_docx = semantic_retriever.index_document(parsed_docx)
        chunks_pdf = semantic_retriever.index_document(parsed_pdf)

        assert len(chunks_txt) > 0
        assert len(chunks_csv) > 0
        assert len(chunks_docx) > 0
        assert len(chunks_pdf) > 0

        # 3. Query CSV Task assignee
        csv_query = "Who is assigned to Document Ingestion Parser?"
        results_csv = semantic_retriever.retrieve(query=csv_query, top_k=3)
        assert len(results_csv) > 0
        assert any("Alice Smith" in r.content or "TASK-101" in r.content for r in results_csv)

        # 4. Query DOCX charter objectives
        docx_query = "What are the project objectives and sprint slippage goals?"
        results_docx = semantic_retriever.retrieve(query=docx_query, top_k=3)
        assert len(results_docx) > 0
        assert any("sprint slippage" in r.content.lower() or "objectives" in r.content.lower() for r in results_docx)

        # 5. Test filter by file_type
        filtered_results = semantic_retriever.retrieve(
            query="AI Project Intelligence",
            top_k=5,
            file_type="csv"
        )
        for r in filtered_results:
            assert r.metadata.file_type.value == "csv"
