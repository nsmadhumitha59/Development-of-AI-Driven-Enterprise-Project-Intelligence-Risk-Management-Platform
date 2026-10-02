import pytest
from app.rag.service import rag_service
from app.schemas import DocumentMetadata

def test_vector_indexing_and_semantic_search():
    meta = DocumentMetadata(
        doc_id="doc_vector_test",
        filename="latency_report.txt",
        file_type="txt",
        file_size_bytes=200,
        char_count=200,
        word_count=30,
        checksum_sha256="testsha256hash",
        uploaded_at="2026-09-04T00:00:00Z"
    )
    doc_text = (
        "Critical Issue: PostgreSQL API Gateway latency has jumped to 450ms. "
        "The primary bottleneck is missing composite database query indices in the user service."
    )
    
    # Index document
    chunks_indexed = rag_service.index_document(meta, doc_text)
    assert chunks_indexed > 0

    # Execute semantic search query
    search_res = rag_service.search("Why is the database slow or having latency?", top_k=3)
    assert search_res.total_hits > 0
    top_hit = search_res.hits[0]
    
    assert top_hit.doc_id == "doc_vector_test"
    assert top_hit.filename == "latency_report.txt"
    assert "latency" in top_hit.text.lower() or "postgresql" in top_hit.text.lower()
    assert top_hit.similarity_score > 0.3

    # Clean up test document
    deleted = rag_service.delete_document("doc_vector_test")
    assert deleted is True
