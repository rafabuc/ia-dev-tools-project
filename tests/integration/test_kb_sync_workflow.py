"""
Integration test for full knowledge base synchronization workflow.

Tests the complete workflow chain:
scan_runbooks_dir → detect_changes → group[regenerate_embeddings tasks] →
update_chromadb → invalidate_cache

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.kb_sync import create_kb_sync_workflow
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestKBSyncWorkflowIntegration:
    """Integration tests for complete KB sync workflow."""

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_complete_kb_sync_workflow_success(
        self,
        mock_cache,
        mock_embedding,
        mock_sync,
        mock_scanner
    ):
        """Test successful execution of complete KB sync workflow."""
        # Arrange
        runbooks_dir = "/runbooks"

        # Mock file scan
        mock_scanner.scan_directory.return_value = {
            "files": [
                {"path": "/runbooks/new.md", "mtime": 1703001235.5},
                {"path": "/runbooks/updated.md", "mtime": 1703001236.5}
            ],
            "total_files": 2
        }

        # Mock change detection
        mock_sync.detect_changes.return_value = {
            "added": ["/runbooks/new.md"],
            "modified": ["/runbooks/updated.md"],
            "deleted": ["/runbooks/old.md"],
            "unchanged": [],
            "total_changes": 3
        }

        # Mock embeddings
        mock_embedding.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 2
        }

        # Mock batch update
        mock_embedding.batch_update.return_value = {
            "updated_count": 2,
            "deleted_count": 1,
            "status": "success"
        }

        # Mock cache invalidation
        mock_cache.invalidate_keys.return_value = {
            "invalidated_keys": 3,
            "status": "success"
        }

        # Act
        workflow = create_kb_sync_workflow(runbooks_dir=runbooks_dir)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        assert result is not None
        # Verify all workflow steps executed
        mock_scanner.scan_directory.assert_called_once()
        mock_sync.detect_changes.assert_called_once()
        mock_embedding.embed_document.assert_called()
        mock_embedding.batch_update.assert_called_once()
        mock_cache.invalidate_keys.assert_called_once()

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    def test_kb_sync_workflow_no_changes(self, mock_sync, mock_scanner):
        """Test workflow when no changes are detected."""
        # Arrange
        runbooks_dir = "/runbooks"

        mock_scanner.scan_directory.return_value = {
            "files": [{"path": "/runbooks/doc.md", "mtime": 1703001234.5}],
            "total_files": 1
        }

        # No changes detected
        mock_sync.detect_changes.return_value = {
            "added": [],
            "modified": [],
            "deleted": [],
            "unchanged": ["/runbooks/doc.md"],
            "total_changes": 0
        }

        # Act
        workflow = create_kb_sync_workflow(runbooks_dir=runbooks_dir)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        # Workflow should complete but skip embedding/update steps
        mock_scanner.scan_directory.assert_called_once()
        mock_sync.detect_changes.assert_called_once()

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    def test_kb_sync_workflow_directory_not_found(self, mock_scanner):
        """Test workflow fails gracefully when directory doesn't exist."""
        # Arrange
        runbooks_dir = "/nonexistent"
        mock_scanner.scan_directory.side_effect = FileNotFoundError("Directory not found")

        # Act
        workflow = create_kb_sync_workflow(runbooks_dir=runbooks_dir)

        # Assert
        with pytest.raises(FileNotFoundError):
            workflow.apply_async().get(timeout=10)

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_kb_sync_workflow_parallel_embeddings(
        self,
        mock_embedding,
        mock_sync,
        mock_scanner
    ):
        """Test that multiple files are embedded in parallel."""
        # Arrange
        runbooks_dir = "/runbooks"

        mock_scanner.scan_directory.return_value = {
            "files": [
                {"path": f"/runbooks/file{i}.md", "mtime": 1703001234.5 + i}
                for i in range(5)
            ],
            "total_files": 5
        }

        mock_sync.detect_changes.return_value = {
            "added": [f"/runbooks/file{i}.md" for i in range(5)],
            "modified": [],
            "deleted": [],
            "unchanged": [],
            "total_changes": 5
        }

        mock_embedding.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 1
        }

        mock_embedding.batch_update.return_value = {
            "updated_count": 5,
            "deleted_count": 0,
            "status": "success"
        }

        # Act
        workflow = create_kb_sync_workflow(runbooks_dir=runbooks_dir)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        # All 5 files should be embedded (possibly in parallel)
        assert mock_embedding.embed_document.call_count == 5

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_kb_sync_workflow_handles_deleted_files(
        self,
        mock_embedding,
        mock_sync,
        mock_scanner
    ):
        """Test that deleted files are properly handled."""
        # Arrange
        runbooks_dir = "/runbooks"

        mock_scanner.scan_directory.return_value = {
            "files": [{"path": "/runbooks/remaining.md", "mtime": 1703001234.5}],
            "total_files": 1
        }

        mock_sync.detect_changes.return_value = {
            "added": [],
            "modified": [],
            "deleted": ["/runbooks/removed1.md", "/runbooks/removed2.md"],
            "unchanged": ["/runbooks/remaining.md"],
            "total_changes": 2
        }

        mock_embedding.batch_update.return_value = {
            "updated_count": 0,
            "deleted_count": 2,
            "status": "success"
        }

        # Act
        workflow = create_kb_sync_workflow(runbooks_dir=runbooks_dir)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        # Deleted files should be removed from ChromaDB
        mock_embedding.batch_update.assert_called_once()
        call_args = mock_embedding.batch_update.call_args
        # Verify deleted files were passed
        assert "removed1" in str(call_args) or "removed2" in str(call_args)

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    @patch('backend.workflows.tasks.kb_sync_tasks.workflow_cache')
    def test_kb_sync_workflow_end_to_end_data_flow(
        self,
        mock_cache,
        mock_embedding,
        mock_sync,
        mock_scanner
    ):
        """Test that data flows correctly through all workflow steps."""
        # Arrange
        runbooks_dir = "/runbooks"

        scanned_files = [
            {"path": "/runbooks/file1.md", "mtime": 1703001235.5},
            {"path": "/runbooks/file2.md", "mtime": 1703001236.5}
        ]
        mock_scanner.scan_directory.return_value = {
            "files": scanned_files,
            "total_files": 2
        }

        changes = {
            "added": ["/runbooks/file2.md"],
            "modified": ["/runbooks/file1.md"],
            "deleted": [],
            "unchanged": [],
            "total_changes": 2
        }
        mock_sync.detect_changes.return_value = changes

        mock_embedding.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 1
        }

        mock_embedding.batch_update.return_value = {
            "updated_count": 2,
            "deleted_count": 0,
            "status": "success"
        }

        mock_cache.invalidate_keys.return_value = {
            "invalidated_keys": 2,
            "status": "success"
        }

        # Act
        workflow = create_kb_sync_workflow(runbooks_dir=runbooks_dir)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        # Verify data flow:
        # 1. Files scanned
        mock_scanner.scan_directory.assert_called_once_with(runbooks_dir)

        # 2. Changes detected
        mock_sync.detect_changes.assert_called_once()

        # 3. Embeddings generated for changed files
        assert mock_embedding.embed_document.call_count == 2

        # 4. ChromaDB updated
        mock_embedding.batch_update.assert_called_once()

        # 5. Cache invalidated
        mock_cache.invalidate_keys.assert_called_once()

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    @patch('backend.workflows.tasks.kb_sync_tasks.embedding_service')
    def test_kb_sync_workflow_first_run(
        self,
        mock_embedding,
        mock_sync,
        mock_scanner
    ):
        """Test workflow behavior on first run (no previous state)."""
        # Arrange
        runbooks_dir = "/runbooks"

        mock_scanner.scan_directory.return_value = {
            "files": [
                {"path": "/runbooks/file1.md", "mtime": 1703001234.5},
                {"path": "/runbooks/file2.md", "mtime": 1703001235.5}
            ],
            "total_files": 2
        }

        # On first run, all files are "added"
        mock_sync.detect_changes.return_value = {
            "added": ["/runbooks/file1.md", "/runbooks/file2.md"],
            "modified": [],
            "deleted": [],
            "unchanged": [],
            "total_changes": 2
        }

        mock_embedding.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "runbooks",
            "status": "embedded",
            "chunks": 1
        }

        mock_embedding.batch_update.return_value = {
            "updated_count": 2,
            "deleted_count": 0,
            "status": "success"
        }

        # Act
        workflow = create_kb_sync_workflow(runbooks_dir=runbooks_dir)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        # All files should be embedded on first run
        assert mock_embedding.embed_document.call_count == 2
        assert result is not None
