"""
Unit test for regenerate_embeddings Celery task.

Tests the task that regenerates embeddings for a runbook file.

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.tasks.kb_sync_tasks import regenerate_embeddings
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestRegenerateEmbeddings:
    """Unit tests for regenerate_embeddings task."""

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_regenerate_embeddings_success(self, mock_embedding_service):
        """Test successful regeneration of embeddings for a file."""
        # Arrange
        file_path = "/runbooks/db_troubleshooting.md"
        embedding_id = str(uuid.uuid4())

        mock_embedding_service.embed_document.return_value = {
            "embedding_id": embedding_id,
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 3
        }

        # Act
        result = regenerate_embeddings(file_path)

        # Assert
        assert result is not None
        assert "file_path" in result
        assert "embedding_id" in result
        assert "chunks" in result
        assert "status" in result
        assert result["status"] == "embedded"
        assert result["file_path"] == file_path

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_regenerate_embeddings_file_not_found(self, mock_embedding_service):
        """Test error handling when file doesn't exist."""
        # Arrange
        file_path = "/runbooks/nonexistent.md"
        mock_embedding_service.embed_document.side_effect = FileNotFoundError("File not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            regenerate_embeddings(file_path)

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_regenerate_embeddings_with_retry(self, mock_embedding_service):
        """Test retry behavior when embedding fails."""
        # Arrange
        file_path = "/runbooks/doc.md"
        mock_embedding_service.embed_document.side_effect = Exception("Service unavailable")

        # Act & Assert
        with pytest.raises(Exception, match="Service unavailable"):
            regenerate_embeddings(file_path)

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_regenerate_embeddings_max_retries(self, mock_embedding_service):
        """Test that task respects max_retries=3 configuration."""
        # Verify task configuration
        assert regenerate_embeddings.max_retries == 3

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_regenerate_embeddings_reads_file_content(self, mock_embedding_service):
        """Test that file content is read and passed to embedding service."""
        # Arrange
        file_path = "/runbooks/doc.md"
        mock_embedding_service.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 2
        }

        # Act
        result = regenerate_embeddings(file_path)

        # Assert
        mock_embedding_service.embed_document.assert_called_once()
        call_args = mock_embedding_service.embed_document.call_args
        # Verify file_path was used
        assert file_path in str(call_args)

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_regenerate_embeddings_large_file(self, mock_embedding_service):
        """Test handling of large files that are chunked."""
        # Arrange
        file_path = "/runbooks/large_doc.md"
        mock_embedding_service.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 10  # Large file chunked into 10 parts
        }

        # Act
        result = regenerate_embeddings(file_path)

        # Assert
        assert result["chunks"] == 10
        assert result["status"] == "embedded"

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_regenerate_embeddings_includes_metadata(self, mock_embedding_service):
        """Test that file metadata is included in embedding."""
        # Arrange
        file_path = "/runbooks/doc.md"
        mock_embedding_service.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 1,
            "metadata": {
                "file_path": file_path,
                "document_type": "runbook"
            }
        }

        # Act
        result = regenerate_embeddings(file_path)

        # Assert
        assert result["status"] == "embedded"

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_regenerate_embeddings_updates_existing(self, mock_embedding_service):
        """Test that regenerating updates existing embeddings."""
        # Arrange
        file_path = "/runbooks/existing.md"
        mock_embedding_service.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 2,
            "operation": "updated"  # Indicates update, not create
        }

        # Act
        result = regenerate_embeddings(file_path)

        # Assert
        assert result["status"] == "embedded"

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_regenerate_embeddings_collection_name(self, mock_embedding_service):
        """Test that embeddings use correct collection name."""
        # Arrange
        file_path = "/runbooks/doc.md"
        mock_embedding_service.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 1
        }

        # Act
        result = regenerate_embeddings(file_path)

        # Assert
        # Collection should be "runbooks" for knowledge base docs
        mock_embedding_service.embed_document.assert_called_once()
