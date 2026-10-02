"""
Semantic Retriever Module coordinating query embedding, vector search, score filtering, and full RAG flow.
"""
from typing import List, Optional, Dict, Any
import logging

from configs.settings import settings
from src.ingestion.base import ParsedDocument
from .chunking import TextChunk, TextChunker
from .embeddings import EmbeddingService
from .vectorstore import BaseVectorStore, ChromaVectorStore
from src.architecture.system_design import RetrievedChunk, ChunkMetadata, DocumentType

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """
    High-level retrieval coordinator.
    Provides methods to:
    1. Index parsed documents (Chunk -> Embed -> Store)
    2. Execute semantic retrieval queries with score thresholds and metadata filters.
    """

    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        chunker: Optional[TextChunker] = None
    ):
        self.embedding_service = embedding_service or EmbeddingService.get_instance()
        self.vector_store = vector_store or ChromaVectorStore()
        self.chunker = chunker or TextChunker()

    def index_document(self, parsed_doc: ParsedDocument) -> List[TextChunk]:
        """
        Executes end-to-end RAG indexing pipeline for a parsed document:
        1. Breaks document into semantic text chunks.
        2. Generates dense embeddings for each chunk.
        3. Upserts chunks and vectors into persistent vector storage.
        
        Returns:
            List of generated TextChunk objects.
        """
        logger.info(f"Indexing document: {parsed_doc.metadata.original_name} (ID: {parsed_doc.metadata.document_id})")

        # 1. Chunk document
        chunks = self.chunker.chunk_document(parsed_doc)
        if not chunks:
            logger.warning(f"No text chunks generated for document {parsed_doc.metadata.original_name}")
            return []

        # 2. Extract chunk texts and generate embeddings
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedding_service.embed_texts(chunk_texts)

        # 3. Store in Vector DB
        self.vector_store.add_chunks(chunks, embeddings)

        logger.info(f"Indexed {len(chunks)} chunks for {parsed_doc.metadata.original_name}")
        return chunks

    def retrieve(
        self,
        query: str,
        top_k: int = settings.DEFAULT_TOP_K,
        document_id: Optional[str] = None,
        file_type: Optional[str] = None,
        min_score: float = settings.SCORE_THRESHOLD
    ) -> List[RetrievedChunk]:
        """
        Performs semantic retrieval against the indexed vector store.
        
        Args:
            query: Natural language query string.
            top_k: Max number of top matches to return.
            document_id: Optional filter to restrict retrieval to a single document.
            file_type: Optional filter by file format (pdf, docx, csv, txt).
            min_score: Score threshold filter (0.0 to 1.0).
            
        Returns:
            List of RetrievedChunk objects with similarity scores and chunk metadata.
        """
        if not query or not query.strip():
            return []

        # Build metadata filters if specified
        filters: Dict[str, Any] = {}
        if document_id and file_type:
            filters = {"$and": [{"document_id": document_id}, {"file_type": file_type}]}
        elif document_id:
            filters = {"document_id": document_id}
        elif file_type:
            filters = {"file_type": file_type}

        # 1. Embed query
        query_vector = self.embedding_service.embed_query(query)

        # 2. Vector search
        search_results = self.vector_store.search(
            query_embedding=query_vector,
            top_k=top_k,
            filters=filters if filters else None
        )

        # 3. Map to standard RetrievedChunk models & apply score filter
        retrieved_chunks: List[RetrievedChunk] = []

        for chunk, score in search_results:
            if score < min_score:
                continue

            try:
                doc_type_enum = DocumentType(chunk.file_type)
            except ValueError:
                doc_type_enum = DocumentType.TXT

            metadata = ChunkMetadata(
                document_id=chunk.document_id,
                filename=chunk.filename,
                file_type=doc_type_enum,
                chunk_index=chunk.chunk_index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                page_number=chunk.page_number,
                row_number=chunk.row_number,
                section_title=chunk.section_title,
                timestamp=chunk.timestamp,
                token_estimate=chunk.token_estimate
            )

            retrieved_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    metadata=metadata,
                    score=score
                )
            )

        return retrieved_chunks

    def delete_document_index(self, document_id: str) -> None:
        """Removes all indexed vectors for the given document."""
        self.vector_store.delete_document(document_id)
