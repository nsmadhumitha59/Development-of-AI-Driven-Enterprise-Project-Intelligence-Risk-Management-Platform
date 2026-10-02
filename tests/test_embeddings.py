"""
Unit tests for SentenceTransformers embedding generation.
"""
import pytest
import numpy as np
from src.rag.embeddings import EmbeddingService


class TestEmbeddingService:
    def test_singleton_instance(self):
        svc1 = EmbeddingService.get_instance()
        svc2 = EmbeddingService.get_instance()
        assert svc1 is svc2

    def test_embed_texts(self, embedding_service):
        texts = [
            "AI Project Intelligence Risk Analysis",
            "Sprint velocity tracking and estimation"
        ]
        embeddings = embedding_service.embed_texts(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 384
        assert len(embeddings[1]) == 384
        assert isinstance(embeddings[0][0], float)

        # Verify unit norm for cosine similarity
        norm = np.linalg.norm(embeddings[0])
        assert np.isclose(norm, 1.0, atol=1e-4)

    def test_embed_query(self, embedding_service):
        query = "What are the project blockers?"
        vector = embedding_service.embed_query(query)

        assert len(vector) == 384
        assert isinstance(vector, list)
