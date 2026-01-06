"""
ChromaDB embedding service for postmortem documents.

Handles document chunking, embedding generation, and ChromaDB operations.
"""

from typing import Dict, Any, List, Optional
import os
import uuid
import hashlib
from datetime import datetime
import chromadb
from chromadb.config import Settings

from backend.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for embedding documents in ChromaDB."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: str = "postmortems"
    ):
        """
        Initialize embedding service.

        Args:
            host: ChromaDB host (defaults to CHROMADB_HOST env var or localhost)
            port: ChromaDB port (defaults to CHROMADB_PORT env var or 8000)
            collection_name: ChromaDB collection name
        """
        self.host = host or os.getenv("CHROMADB_HOST", "chromadb")
        self.port = port or int(os.getenv("CHROMADB_PORT", "8000"))
        self.collection_name = collection_name

        # Initialize ChromaDB client
        try:
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=Settings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )

            heartbeat = self.client.heartbeat()
            logger.info(f"ChromaDB heartbeat: {heartbeat}")
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Postmortem documents for RAG"}
            )

            logger.info(
                f"Embedding service initialized: {self.host}:{self.port}, "
                f"collection={self.collection_name}"
            )
        except Exception as exc:
            logger.error(f"Failed to initialize ChromaDB client: {exc}")
            raise

    def embed_document(
        self,
        incident_id: str,
        document: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Embed postmortem document in ChromaDB.

        Large documents are automatically chunked for better retrieval.

        Args:
            incident_id: Incident UUID
            document: Postmortem document text
            metadata: Optional metadata to store with document

        Returns:
            Dict containing:
            - embedding_id: UUID of the embedding
            - collection: ChromaDB collection name
            - status: "indexed" or "failed"
            - chunks: Number of chunks created (if document was chunked)
            - operation: "created" or "updated"

        Raises:
            ValueError: If document is empty
            Exception: If ChromaDB operation fails
        """
        logger.info(f"Embedding document for incident {incident_id}")

        # Validate document  TODO RBM
        if not document: #or not document.strip():
            raise ValueError("Cannot embed empty document")

        # Prepare metadata
        doc_metadata = metadata or {}
        doc_metadata.update({
            "incident_id": incident_id,
            "document_type": "postmortem",
            "indexed_at": datetime.now().isoformat(),
            "char_count": len(document)
        })

        # Check if document already exists
        existing = self._check_existing_document(incident_id)

        try:
            # Chunk document if it's large
            chunks = self._chunk_document(document)
            logger.info(f"Document chunked into {len(chunks)} parts")

            # Generate embedding IDs
            embedding_ids = [
                str(uuid.uuid4()) for _ in range(len(chunks))
            ]

            # Add chunk metadata
            chunk_metadata = []
            for i, chunk in enumerate(chunks):
                chunk_meta = doc_metadata.copy()
                chunk_meta["chunk_index"] = i
                chunk_meta["total_chunks"] = len(chunks)
                chunk_meta["chunk_char_count"] = len(chunk)
                chunk_metadata.append(chunk_meta)

            # Upsert to ChromaDB
            self.collection.upsert(
                ids=embedding_ids,
                documents=chunks,
                metadatas=chunk_metadata
            )

            operation = "updated" if existing else "created"
            logger.info(
                f"Successfully embedded document for incident {incident_id}, "
                f"operation={operation}, chunks={len(chunks)}"
            )

            return {
                "embedding_id": embedding_ids[0],  # Primary embedding ID
                "collection": self.collection_name,
                "status": "indexed",
                "chunks": len(chunks),
                "operation": operation
            }

        except Exception as exc:
            logger.error(f"ChromaDB embedding failed for incident {incident_id}: {exc}")
            raise

    def _chunk_document(
        self,
        document: str,
        max_chunk_size: int = 1000,
        overlap: int = 100
    ) -> List[str]:
        """
        Chunk document into smaller parts for better retrieval.

        Args:
            document: Document to chunk
            max_chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks

        Returns:
            List of document chunks
        """
        if len(document) <= max_chunk_size:
            return [document]

        chunks = []
        start = 0

        while start < len(document):
            end = start + max_chunk_size

            # Try to break at sentence boundary
            if end < len(document):
                # Look for sentence ending in the last 100 chars
                last_period = document.rfind(".", start, end)
                last_newline = document.rfind("\n\n", start, end)
                break_point = max(last_period, last_newline)

                if break_point > start + (max_chunk_size // 2):
                    end = break_point + 1

            chunk = document[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start forward with overlap
            start = end - overlap

        return chunks

    def _check_existing_document(self, incident_id: str) -> bool:
        """
        Check if document already exists in ChromaDB.

        Args:
            incident_id: Incident UUID

        Returns:
            True if document exists, False otherwise
        """
        try:
            results = self.collection.get(
                where={"incident_id": incident_id}
            )
            return len(results["ids"]) > 0
        except Exception:
            return False

    def search_similar_documents(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar postmortem documents.

        Args:
            query: Search query
            n_results: Number of results to return

        Returns:
            List of similar documents with metadata and scores
        """
        logger.info(f"Searching for similar documents: query='{query[:50]}...'")

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )

            documents = []
            for i in range(len(results["ids"][0])):
                documents.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })

            logger.info(f"Found {len(documents)} similar documents")
            return documents

        except Exception as exc:
            logger.error(f"ChromaDB search failed: {exc}")
            raise

    def delete_document(self, incident_id: str) -> Dict[str, Any]:
        """
        Delete document from ChromaDB.

        Args:
            incident_id: Incident UUID

        Returns:
            Dict containing deletion status
        """
        logger.info(f"Deleting document for incident {incident_id}")

        try:
            self.collection.delete(
                where={"incident_id": incident_id}
            )

            logger.info(f"Successfully deleted document for incident {incident_id}")
            return {
                "incident_id": incident_id,
                "status": "deleted"
            }

        except Exception as exc:
            logger.error(f"ChromaDB deletion failed for incident {incident_id}: {exc}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.

        Returns:
            Dict containing collection stats
        """
        try:
            count = self.collection.count()
            return {
                "collection": self.collection_name,
                "document_count": count
            }
        except Exception as exc:
            logger.error(f"Failed to get collection stats: {exc}")
            raise

    def batch_update(
        self,
        embeddings: List[Dict[str, Any]],
        deleted_files: List[str] = None
    ) -> Dict[str, Any]:
        """
        Batch update ChromaDB with new/modified embeddings and deletions.

        Args:
            embeddings: List of embedding dicts with file_path, embedding_id, chunks
            deleted_files: List of file paths to delete

        Returns:
            Dict containing:
            - updated_count: Number of embeddings updated
            - deleted_count: Number of embeddings deleted
            - status: "success", "partial", or "failed"
        """
        deleted_files = deleted_files or []
        logger.info(
            f"Batch update: {len(embeddings)} updates, {len(deleted_files)} deletions"
        )

        updated_count = 0
        deleted_count = 0

        try:
            # Delete removed files first
            for file_path in deleted_files:
                try:
                    self.delete_document(file_path)
                    deleted_count += 1
                except Exception as exc:
                    logger.warning(f"Failed to delete {file_path}: {exc}")

            # Note: Embeddings are already in ChromaDB from regenerate_embeddings task
            # This method just tracks the count
            updated_count = len(embeddings)

            status = "success"
            if updated_count < len(embeddings) or deleted_count < len(deleted_files):
                status = "partial"

            logger.info(
                f"Batch update complete: {updated_count} updated, {deleted_count} deleted"
            )

            return {
                "updated_count": updated_count,
                "deleted_count": deleted_count,
                "status": status
            }

        except Exception as exc:
            logger.error(f"Batch update failed: {exc}")
            return {
                "updated_count": updated_count,
                "deleted_count": deleted_count,
                "status": "failed",
                "error": str(exc)
            }


# Global embedding service instance
embedding_service = EmbeddingService()
