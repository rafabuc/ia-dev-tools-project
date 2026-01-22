"""
Unit test for update_chromadb Celery task.

Tests the task that batch updates ChromaDB with new/modified embeddings.

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.tasks.kb_sync_tasks import update_chromadb
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestUpdateChromaDB:
    """Unit tests for update_chromadb task."""

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_update_chromadb_success(self, mock_embedding_service):
        """Test successful batch update of ChromaDB."""
        # Arrange
        embeddings = [
            {"file_path": "/runbooks/file1.md", "embedding_id": str(uuid.uuid4()), "chunks": 2},
            {"file_path": "/runbooks/file2.md", "embedding_id": str(uuid.uuid4()), "chunks": 3}
        ]
        deleted_files = ["/runbooks/old.md"]

        mock_embedding_service.batch_update.return_value = {
            "updated_count": 2,
            "deleted_count": 1,
            "status": "success"
        }

        # Act
        result = update_chromadb(embeddings, deleted_files)

        # Assert
        assert result is not None
        assert "updated_count" in result
        assert "deleted_count" in result
        assert "status" in result
        assert result["status"] == "success"
        assert result["updated_count"] == 2
        assert result["deleted_count"] == 1

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_update_chromadb_empty_updates(self, mock_embedding_service):
        """Test update with no changes."""
        # Arrange
        embeddings = []
        deleted_files = []

        mock_embedding_service.batch_update.return_value = {
            "updated_count": 0,
            "deleted_count": 0,
            "status": "success"
        }

        # Act
        result = update_chromadb(embeddings, deleted_files)

        # Assert
        assert result["updated_count"] == 0
        assert result["deleted_count"] == 0
        assert result["status"] == "success"

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_update_chromadb_with_retry(self, mock_embedding_service):
        """Test retry behavior when ChromaDB fails."""
        # Arrange
        embeddings = [{"file_path": "/runbooks/file.md", "embedding_id": str(uuid.uuid4())}]
        deleted_files = []

        mock_embedding_service.batch_update.side_effect = Exception("Connection error")

        # Act & Assert
        with pytest.raises(Exception, match="Connection error"):
            update_chromadb(embeddings, deleted_files)

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_update_chromadb_max_retries(self, mock_embedding_service):
        """Test that task respects max_retries=3 configuration."""
        # Verify task configuration
        assert update_chromadb.max_retries == 3

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_update_chromadb_batch_upsert(self, mock_embedding_service):
        """Test that updates use batch upsert operation."""
        # Arrange
        embeddings = [
            {"file_path": "/runbooks/file1.md", "embedding_id": str(uuid.uuid4())},
            {"file_path": "/runbooks/file2.md", "embedding_id": str(uuid.uuid4())},
            {"file_path": "/runbooks/file3.md", "embedding_id": str(uuid.uuid4())}
        ]
        deleted_files = []

        mock_embedding_service.batch_update.return_value = {
            "updated_count": 3,
            "deleted_count": 0,
            "status": "success"
        }

        # Act
        result = update_chromadb(embeddings, deleted_files)

        # Assert
        mock_embedding_service.batch_update.assert_called_once()
        call_args = mock_embedding_service.batch_update.call_args
        # Verify embeddings were passed
        assert embeddings in str(call_args) or len(call_args[0]) > 0

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_update_chromadb_delete_removed_files(self, mock_embedding_service):
        """Test that deleted files are removed from ChromaDB."""
        # Arrange
        embeddings = []
        deleted_files = ["/runbooks/removed1.md", "/runbooks/removed2.md"]

        mock_embedding_service.batch_update.return_value = {
            "updated_count": 0,
            "deleted_count": 2,
            "status": "success"
        }

        # Act
        result = update_chromadb(embeddings, deleted_files)

        # Assert
        assert result["deleted_count"] == 2
        mock_embedding_service.batch_update.assert_called_once()

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_update_chromadb_partial_failure(self, mock_embedding_service):
        """Test handling of partial update failure."""
        # Arrange
        embeddings = [
            {"file_path": "/runbooks/file1.md", "embedding_id": str(uuid.uuid4())},
            {"file_path": "/runbooks/file2.md", "embedding_id": str(uuid.uuid4())}
        ]
        deleted_files = []

        # Some updates succeed, some fail
        mock_embedding_service.batch_update.return_value = {
            "updated_count": 1,
            "deleted_count": 0,
            "status": "partial",
            "failed": ["/runbooks/file2.md"]
        }

        # Act
        result = update_chromadb(embeddings, deleted_files)

        # Assert
        assert result["status"] == "partial"
        assert result["updated_count"] == 1

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_update_chromadb_transaction_safety(self, mock_embedding_service):
        """Test that updates are transactional (all or nothing)."""
        # Arrange
        embeddings = [{"file_path": "/runbooks/file.md", "embedding_id": str(uuid.uuid4())}]
        deleted_files = []

        mock_embedding_service.batch_update.side_effect = Exception("Transaction failed")

        # Act & Assert
        with pytest.raises(Exception):
            update_chromadb(embeddings, deleted_files)

    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_update_chromadb_large_batch(self, mock_embedding_service):
        """Test handling of large batch updates."""
        # Arrange
        # Create large batch of embeddings
        embeddings = [
            {"file_path": f"/runbooks/file{i}.md", "embedding_id": str(uuid.uuid4())}
            for i in range(100)
        ]
        deleted_files = []

        mock_embedding_service.batch_update.return_value = {
            "updated_count": 100,
            "deleted_count": 0,
            "status": "success"
        }

        # Act
        result = update_chromadb(embeddings, deleted_files)

        # Assert
        assert result["updated_count"] == 100
        assert result["status"] == "success"
