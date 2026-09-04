from typing import List
from sentence_transformers import SentenceTransformer
from app.config import settings

class EmbeddingGenerator:
    """
    SentenceTransformers embedding generator using all-MiniLM-L6-v2.
    Produces 384-dimensional dense vectors.
    """
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            print(f"[EmbeddingGenerator] Loading SentenceTransformer model '{self.model_name}'...")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for a single string."""
        if not text:
            return [0.0] * 384
        vector = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return vector.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of text strings."""
        if not texts:
            return []
        vectors = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False, batch_size=32)
        return vectors.tolist()

embedding_generator = EmbeddingGenerator()
