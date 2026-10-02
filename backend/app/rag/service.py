from typing import List, Optional
from app.schemas import DocumentMetadata, Chunk, SearchResponse, SearchHit
from app.rag.chunker import chunker
from app.rag.embeddings import embedding_generator
from app.rag.vector_store import vector_store
from app.ingestion.metadata import metadata_store

class RAGService:
    """
    Unified RAG Service interface:
    - Text chunking
    - Vector embedding generation
    - Persistent ChromaDB indexing
    - Semantic similarity retrieval
    """
    def index_document(self, metadata: DocumentMetadata, text: str) -> int:
        """
        Chunks normalized document text, generates vectors via SentenceTransformers,
        and indexes chunks in persistent ChromaDB.
        Returns total number of chunks created.
        """
        # 1. Chunk document
        chunks: List[Chunk] = chunker.chunk_document(text, metadata)
        if not chunks:
            return 0

        # 2. Extract chunk text strings for batch embedding
        chunk_texts = [c.text for c in chunks]

        # 3. Generate embeddings
        embeddings = embedding_generator.generate_embeddings_batch(chunk_texts)

        # 4. Add to vector store
        vector_store.add_chunks(chunks, embeddings)

        # 5. Update metadata with chunk count
        metadata.chunk_count = len(chunks)
        metadata_store.add_document(metadata)

        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_id: Optional[str] = None,
        file_type: Optional[str] = None
    ) -> SearchResponse:
        """
        Generates query embedding vector and retrieves top-k matching chunks from vector store.
        """
        if not query or not query.strip():
            return SearchResponse(query=query, total_hits=0, hits=[])

        # Generate query vector
        query_vector = embedding_generator.generate_embedding(query)

        # Vector similarity search
        hits: List[SearchHit] = vector_store.search(
            query_embedding=query_vector,
            top_k=top_k,
            doc_id=doc_id,
            file_type=file_type
        )

        return SearchResponse(
            query=query,
            total_hits=len(hits),
            hits=hits
        )

    def delete_document(self, doc_id: str) -> bool:
        """Deletes document metadata and purges vector chunks."""
        vector_store.delete_document_chunks(doc_id)
        return metadata_store.delete_document(doc_id)

rag_service = RAGService()
