"""
Unit tests for local ChromaVectorStore indexing, search, and deletion.
"""
import pytest
from src.rag.chunking import TextChunk
from src.rag.vectorstore import ChromaVectorStore


class TestChromaVectorStore:
    def test_add_and_search_chunks(self, test_vector_store, embedding_service):
        chunks = [
            TextChunk(
                chunk_id="chunk-1",
                document_id="doc-101",
                filename="sprint_notes.txt",
                file_type="txt",
                chunk_index=0,
                content="Critical Risk: The payment gateway migration has delayed checkout integration.",
                start_char=0,
                end_char=75
            ),
            TextChunk(
                chunk_id="chunk-2",
                document_id="doc-102",
                filename="ui_design.txt",
                file_type="txt",
                chunk_index=0,
                content="The dark theme CSS styles have been updated for dashboard glassmorphism.",
                start_char=0,
                end_char=70
            )
        ]

        # Generate embeddings
        embeddings = embedding_service.embed_texts([c.content for c in chunks])

        # Add to vector store
        test_vector_store.add_chunks(chunks, embeddings)

        stats = test_vector_store.get_stats()
        assert stats["total_chunks_indexed"] >= 2

        # Search query for payment gateway risk
        query_vec = embedding_service.embed_query("payment gateway delay risk")
        results = test_vector_store.search(query_vec, top_k=2)

        assert len(results) > 0
        top_chunk, score = results[0]
        assert top_chunk.chunk_id == "chunk-1"
        assert score > 0.4

    def test_delete_document(self, test_vector_store, embedding_service):
        chunk = TextChunk(
            chunk_id="chunk-to-delete",
            document_id="doc-delete-test",
            filename="temp.txt",
            file_type="txt",
            chunk_index=0,
            content="Temporary chunk for deletion test.",
            start_char=0,
            end_char=35
        )
        emb = embedding_service.embed_texts([chunk.content])
        test_vector_store.add_chunks([chunk], emb)

        # Delete
        test_vector_store.delete_document("doc-delete-test")

        # Query and ensure not found
        query_vec = embedding_service.embed_query("Temporary chunk for deletion")
        results = test_vector_store.search(query_vec, top_k=5, filters={"document_id": "doc-delete-test"})
        assert len(results) == 0
