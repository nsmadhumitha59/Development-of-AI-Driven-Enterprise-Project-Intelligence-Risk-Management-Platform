"""
Vector Database Store using ChromaDB for persistent local indexing.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
import chromadb
from chromadb.config import Settings as ChromaSettings

from configs.settings import settings
from .chunking import TextChunk

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """Abstract interface for vector database implementations."""

    @abstractmethod
    def add_chunks(self, chunks: List[TextChunk], embeddings: List[List[float]]) -> None:
        """Indexes chunks with their corresponding dense embeddings."""
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[TextChunk, float]]:
        """Searches index for most similar chunks, returning list of (chunk, similarity_score)."""
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        """Removes all indexed chunks associated with a document ID."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Returns index metrics such as total vector count."""
        pass


class ChromaVectorStore(BaseVectorStore):
    """
    Persistent local vector store powered by ChromaDB.
    Persists collection embeddings and metadata to disk.
    """

    def __init__(
        self,
        persist_directory: Optional[Path] = None,
        collection_name: str = settings.VECTOR_COLLECTION_NAME
    ):
        self.persist_directory = str(persist_directory or settings.VECTOR_DB_DIR)
        self.collection_name = collection_name
        
        # Initialize persistent Chroma client
        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection with cosine similarity space
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Initialized ChromaDB at {self.persist_directory} [Collection: {self.collection_name}]")

    def add_chunks(self, chunks: List[TextChunk], embeddings: List[List[float]]) -> None:
        """
        Inserts or updates text chunks and their embeddings into ChromaDB collection.
        """
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch between number of chunks ({len(chunks)}) and embeddings ({len(embeddings)})")

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        
        # Flatten metadata for ChromaDB compatibility (primitive types only)
        metadatas = []
        for chunk in chunks:
            meta: Dict[str, Any] = {
                "document_id": chunk.document_id,
                "filename": chunk.filename,
                "file_type": chunk.file_type,
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "timestamp": chunk.timestamp,
                "char_count": chunk.char_count,
                "token_estimate": chunk.token_estimate,
                "section_title": chunk.section_title or ""
            }
            if chunk.page_number is not None:
                meta["page_number"] = chunk.page_number
            if chunk.row_number is not None:
                meta["row_number"] = chunk.row_number

            metadatas.append(meta)

        # Batch upsert into Chroma
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Successfully indexed {len(chunks)} chunks into vector store.")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = settings.DEFAULT_TOP_K,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[TextChunk, float]]:
        """
        Queries the vector collection for nearest neighbors using cosine similarity.
        
        Returns:
            List of (TextChunk, similarity_score) sorted by score descending.
        """
        count = self._collection.count()
        if count == 0:
            return []

        actual_k = min(top_k, count)
        
        query_args: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": actual_k,
            "include": ["documents", "metadatas", "distances"]
        }
        
        if filters:
            query_args["where"] = filters

        try:
            results = self._collection.query(**query_args)
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}", exc_info=True)
            return []

        retrieved: List[Tuple[TextChunk, float]] = []

        if results and results["ids"] and len(results["ids"]) > 0:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else []
            metas = results["metadatas"][0] if results.get("metadatas") else []
            distances = results["distances"][0] if results.get("distances") else []

            for idx in range(len(ids)):
                chunk_id = ids[idx]
                content = docs[idx] if idx < len(docs) else ""
                meta_dict = metas[idx] if idx < len(metas) else {}
                raw_dist = distances[idx] if idx < len(distances) else 1.0

                # Chroma with cosine distance returns distance d in [0, 2].
                # Cosine similarity = 1 - (distance / 2) or standard 1 - distance
                similarity_score = max(0.0, min(1.0, 1.0 - (raw_dist / 2.0 if raw_dist > 1.0 else raw_dist)))

                chunk = TextChunk(
                    chunk_id=chunk_id,
                    document_id=meta_dict.get("document_id", "unknown"),
                    filename=meta_dict.get("filename", "unknown"),
                    file_type=meta_dict.get("file_type", "txt"),
                    chunk_index=meta_dict.get("chunk_index", 0),
                    content=content,
                    start_char=meta_dict.get("start_char", 0),
                    end_char=meta_dict.get("end_char", len(content)),
                    page_number=meta_dict.get("page_number"),
                    row_number=meta_dict.get("row_number"),
                    section_title=meta_dict.get("section_title"),
                    timestamp=meta_dict.get("timestamp", ""),
                    char_count=meta_dict.get("char_count", len(content)),
                    token_estimate=meta_dict.get("token_estimate", len(content) // 4)
                )

                retrieved.append((chunk, round(similarity_score, 4)))

        return retrieved

    def delete_document(self, document_id: str) -> None:
        """Deletes all chunks belonging to the given document_id."""
        try:
            self._collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted vector chunks for document_id={document_id}")
        except Exception as e:
            logger.error(f"Error deleting vectors for document {document_id}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Returns collection size and stats."""
        return {
            "collection_name": self.collection_name,
            "total_chunks_indexed": self._collection.count(),
            "persist_directory": self.persist_directory
        }

    def reset(self) -> None:
        """Clears all vectors in collection (used primarily for test isolation)."""
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
