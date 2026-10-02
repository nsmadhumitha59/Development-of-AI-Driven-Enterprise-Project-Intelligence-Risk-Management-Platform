"""
Embedding Generation Service using SentenceTransformers.
"""
import logging
from typing import List, Optional, Union
import numpy as np

from configs.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Manages local SentenceTransformers embedding generation.
    Lazily initializes and caches the neural embedding model.
    """

    _instance: Optional["EmbeddingService"] = None

    def __init__(
        self,
        model_name: str = settings.EMBEDDING_MODEL_NAME,
        device: str = settings.EMBEDDING_DEVICE,
        batch_size: int = settings.EMBEDDING_BATCH_SIZE
    ):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = None
        self._dimension = settings.EMBEDDING_DIMENSION

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        """Singleton accessor for the embedding service."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self):
        """Lazily load SentenceTransformer model into memory."""
        if self._model is None:
            logger.info(f"Loading SentenceTransformer embedding model: {self.model_name} on {self.device}...")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device)
                logger.info("Embedding model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load embedding model {self.model_name}: {e}", exc_info=True)
                raise RuntimeError(f"Could not load embedding model: {str(e)}") from e

    @property
    def dimension(self) -> int:
        """Vector dimension of generated embeddings (e.g. 384 for all-MiniLM-L6-v2)."""
        self._load_model()
        return self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """
        Generates dense vector embeddings for a list of input texts.
        
        Args:
            texts: List of text strings to embed.
            normalize: Whether to L2-normalize vectors for cosine similarity.
            
        Returns:
            List of float vector embeddings.
        """
        if not texts:
            return []

        self._load_model()

        # Handle empty/blank texts by replacing with single space to avoid tokenizer failure
        cleaned_texts = [t if (t and t.strip()) else " " for t in texts]

        embeddings = self._model.encode(
            cleaned_texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=normalize,
            convert_to_numpy=True
        )

        return embeddings.tolist()

    def embed_query(self, query: str, normalize: bool = True) -> List[float]:
        """
        Generates embedding for a single search query text.
        
        Args:
            query: Query string.
            normalize: Whether to L2-normalize vector.
            
        Returns:
            Vector embedding as list of floats.
        """
        cleaned_query = query.strip() if query else " "
        embeddings = self.embed_texts([cleaned_query], normalize=normalize)
        return embeddings[0]
