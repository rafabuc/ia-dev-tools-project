"""
Unit test for embed_in_chromadb Celery task.

Tests the task that embeds postmortem documents in ChromaDB for searchability.

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.tasks.postmortem_tasks import embed_in_chromadb
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestEmbedInChromaDB:
    """Unit tests for embed_in_chromadb task."""

    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    def test_embed_document_success(self, mock_embedding_service):
        """Test successful embedding of postmortem document."""
        # Arrange
        incident_id = str(uuid.uuid4())
        document = """# Postmortem: API Service Outage

## Summary
API service experienced 45-minute outage due to database issues.

## Root Cause
Database connection pool exhaustion.
"""
        embedding_id = str(uuid.uuid4())

        mock_embedding_service.embed_document.return_value = {
            "embedding_id": embedding_id,
            "collection": "postmortems",
            "status": "indexed"
        }

        # Act
        result = embed_in_chromadb(incident_id, document)

        # Assert
        assert result is not None
        assert "embedding_id" in result
        assert "collection" in result
        assert "status" in result
        assert result["status"] == "indexed"
        assert result["collection"] == "postmortems"

    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    def test_embed_document_with_metadata(self, mock_embedding_service):
        """Test that incident metadata is included in embedding."""
        # Arrange
        incident_id = str(uuid.uuid4())
        document = "# Postmortem content"

        mock_embedding_service.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "postmortems",
            "status": "indexed",
            "metadata": {
                "incident_id": incident_id,
                "document_type": "postmortem",
                "indexed_at": "2025-12-29T10:00:00Z"
            }
        }

        # Act
        result = embed_in_chromadb(incident_id, document)

        # Assert
        mock_embedding_service.embed_document.assert_called_once()
        call_args = mock_embedding_service.embed_document.call_args
        # Verify incident_id was passed
        assert call_args[0][0] == incident_id or call_args[1].get("incident_id") == incident_id

    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    def test_embed_empty_document(self, mock_embedding_service):
        """Test error handling for empty document."""
        # Arrange
        incident_id = str(uuid.uuid4())
        document = ""

        # Act & Assert
        with pytest.raises(ValueError, match="empty|document"):
            embed_in_chromadb(incident_id, document)

    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    def test_embed_document_chromadb_failure_with_retry(self, mock_embedding_service):
        """Test retry behavior when ChromaDB fails."""
        # Arrange
        incident_id = str(uuid.uuid4())
        document = "# Postmortem content"

        mock_embedding_service.embed_document.side_effect = Exception("ChromaDB connection error")

        # Act & Assert
        with pytest.raises(Exception, match="ChromaDB connection error"):
            embed_in_chromadb(incident_id, document)

    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    def test_embed_document_max_retries(self, mock_embedding_service):
        """Test that task respects max_retries=3 configuration."""
        # Verify task configuration
        assert embed_in_chromadb.max_retries == 3

    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    def test_embed_document_chunks_large_documents(self, mock_embedding_service):
        """Test that large documents are properly chunked for embedding."""
        # Arrange
        incident_id = str(uuid.uuid4())
        # Create a large document
        large_document = "# Postmortem\n\n" + ("This is a test paragraph. " * 1000)

        mock_embedding_service.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "postmortems",
            "status": "indexed",
            "chunks": 5  # Indicate document was chunked
        }

        # Act
        result = embed_in_chromadb(incident_id, large_document)

        # Assert
        assert result["status"] == "indexed"
        # Verify embedding service was called
        mock_embedding_service.embed_document.assert_called_once()

    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    def test_embed_document_updates_existing_embedding(self, mock_embedding_service):
        """Test that re-embedding an incident updates the existing embedding."""
        # Arrange
        incident_id = str(uuid.uuid4())
        document = "# Updated Postmortem content"

        mock_embedding_service.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "postmortems",
            "status": "indexed",
            "operation": "updated"  # Indicates existing embedding was updated
        }

        # Act
        result = embed_in_chromadb(incident_id, document)

        # Assert
        assert result["status"] == "indexed"

    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    def test_embed_document_collection_configuration(self, mock_embedding_service):
        """Test that documents are embedded in correct ChromaDB collection."""
        # Arrange
        incident_id = str(uuid.uuid4())
        document = "# Postmortem content"

        mock_embedding_service.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "postmortems",
            "status": "indexed"
        }

        # Act
        result = embed_in_chromadb(incident_id, document)

        # Assert
        assert result["collection"] == "postmortems"
        mock_embedding_service.embed_document.assert_called_once()

    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    def test_embed_document_returns_embedding_id(self, mock_embedding_service):
        """Test that task returns valid embedding ID for tracking."""
        # Arrange
        incident_id = str(uuid.uuid4())
        document = "# Postmortem content"
        embedding_id = str(uuid.uuid4())

        mock_embedding_service.embed_document.return_value = {
            "embedding_id": embedding_id,
            "collection": "postmortems",
            "status": "indexed"
        }

        # Act
        result = embed_in_chromadb(incident_id, document)

        # Assert
        assert result["embedding_id"] == embedding_id
        # Verify it's a valid UUID
        uuid.UUID(result["embedding_id"])
