import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from app.config import settings
from app.schemas import Chunk, SearchHit

class VectorStore:
    """
    Local persistent vector database interface powered by ChromaDB.
    Indexed chunks include full metadata for fine-grained retrieval filtering.
    """
    def __init__(self, persistent_path: str = settings.CHROMA_DB_DIR):
        self.persistent_path = persistent_path
        self._client = None
        self._collection = None

    @property
    def client(self):
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self.persistent_path)
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="project_documents",
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]):
        """Upsert document text chunks into ChromaDB with embeddings and metadata."""
        if not chunks or not embeddings:
            return

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "filename": c.filename,
                "file_type": c.file_type,
                "chunk_index": c.chunk_index,
                "char_length": c.char_length,
                "start_char": c.start_char,
                "end_char": c.end_char
            }
            for c in chunks
        ]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = settings.TOP_K_RESULTS,
        doc_id: Optional[str] = None,
        file_type: Optional[str] = None
    ) -> List[SearchHit]:
        """
        Executes cosine similarity search over vector store and returns SearchHit objects with scores.
        """
        where_filter = {}
        if doc_id and file_type:
            where_filter = {"$and": [{"doc_id": doc_id}, {"file_type": file_type}]}
        elif doc_id:
            where_filter = {"doc_id": doc_id}
        elif file_type:
            where_filter = {"file_type": file_type}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )

        hits: List[SearchHit] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return hits

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for chunk_id, doc_text, meta, dist in zip(ids, docs, metas, distances):
            # ChromaDB cosine distance range: [0, 2]. Similarity = 1 - distance
            similarity = max(0.0, min(1.0, 1.0 - (dist if dist is not None else 1.0)))
            hits.append(
                SearchHit(
                    chunk_id=chunk_id,
                    doc_id=meta.get("doc_id", ""),
                    filename=meta.get("filename", ""),
                    file_type=meta.get("file_type", ""),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    text=doc_text,
                    similarity_score=round(similarity, 4),
                    distance=round(float(dist) if dist is not None else 1.0, 4)
                )
            )

        # Sort hits by similarity descending
        hits.sort(key=lambda x: x.similarity_score, reverse=True)
        return hits

    def delete_document_chunks(self, doc_id: str):
        """Purge all vector chunks associated with doc_id."""
        try:
            self.collection.delete(where={"doc_id": doc_id})
        except Exception as e:
            print(f"[VectorStore] Warning during deletion of doc {doc_id}: {e}")

    def get_stats() -> Dict[str, Any]:
        """Get vector store count and stats."""
        try:
            return {"total_chunks": self.collection.count()}
        except Exception:
            return {"total_chunks": 0}

vector_store = VectorStore()
