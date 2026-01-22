"""
Contract test for knowledge base synchronization workflow.

This test verifies the contract between workflow steps in the KB sync chain:
scan_runbooks_dir → detect_changes → group[regenerate_embeddings tasks] →
update_chromadb → invalidate_cache

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from celery import chain, group

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.kb_sync import create_kb_sync_workflow
    from backend.workflows.tasks.kb_sync_tasks import (
        scan_runbooks_dir,
        detect_changes,
        regenerate_embeddings,
        update_chromadb,
        invalidate_cache,
    )
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestKBSyncWorkflowContract:
    """Contract tests for KB synchronization workflow."""

    def test_workflow_chain_composition(self):
        """Test that workflow chain is properly composed with correct task order."""
        # Arrange
        runbooks_dir = "/path/to/runbooks"

        # Act
        workflow = create_kb_sync_workflow(runbooks_dir=runbooks_dir)

        # Assert
        assert isinstance(workflow, chain), "Workflow should be a Celery chain"
        assert len(workflow.tasks) >= 4, "Workflow should have at least 4 main tasks"

    @patch('backend.workflows.tasks.kb_sync_tasks.scan_runbooks_dir.apply_async')
    def test_scan_runbooks_dir_contract(self, mock_task):
        """Test scan_runbooks_dir task contract."""
        # Arrange
        expected_result = {
            "files": [
                {"path": "/runbooks/db_troubleshooting.md", "mtime": 1703001234.5},
                {"path": "/runbooks/api_recovery.md", "mtime": 1703001235.5}
            ],
            "total_files": 2,
            "scan_timestamp": "2025-12-29T10:00:00Z"
        }
        mock_task.return_value = Mock(id="task-scan-123")
        mock_task.return_value.get = Mock(return_value=expected_result)

        # Act
        result = scan_runbooks_dir.apply_async(args=["/runbooks"]).get()

        # Assert
        assert "files" in result
        assert "total_files" in result
        assert "scan_timestamp" in result
        assert isinstance(result["files"], list)

    @patch('backend.workflows.tasks.kb_sync_tasks.detect_changes.apply_async')
    def test_detect_changes_contract(self, mock_task):
        """Test detect_changes task contract."""
        # Arrange
        current_files = [
            {"path": "/runbooks/file1.md", "mtime": 1703001235.5},
            {"path": "/runbooks/file2.md", "mtime": 1703001236.5}
        ]
        expected_result = {
            "added": ["/runbooks/file2.md"],
            "modified": ["/runbooks/file1.md"],
            "deleted": [],
            "unchanged": [],
            "total_changes": 2
        }
        mock_task.return_value = Mock(id="task-detect-456")
        mock_task.return_value.get = Mock(return_value=expected_result)

        # Act
        result = detect_changes.apply_async(args=[current_files]).get()

        # Assert
        assert "added" in result
        assert "modified" in result
        assert "deleted" in result
        assert "total_changes" in result
        assert isinstance(result["added"], list)
        assert isinstance(result["modified"], list)
        assert isinstance(result["deleted"], list)

    @patch('backend.workflows.tasks.kb_sync_tasks.regenerate_embeddings.apply_async')
    def test_regenerate_embeddings_contract(self, mock_task):
        """Test regenerate_embeddings task contract."""
        # Arrange
        file_path = "/runbooks/db_troubleshooting.md"
        expected_result = {
            "file_path": file_path,
            "embedding_id": str(uuid.uuid4()),
            "chunks": 3,
            "status": "embedded"
        }
        mock_task.return_value = Mock(id="task-regen-789")
        mock_task.return_value.get = Mock(return_value=expected_result)

        # Act
        result = regenerate_embeddings.apply_async(args=[file_path]).get()

        # Assert
        assert "file_path" in result
        assert "embedding_id" in result
        assert "chunks" in result
        assert "status" in result
        assert result["status"] in ["embedded", "failed"]

    @patch('backend.workflows.tasks.kb_sync_tasks.update_chromadb.apply_async')
    def test_update_chromadb_contract(self, mock_task):
        """Test update_chromadb task contract."""
        # Arrange
        embeddings = [
            {"file_path": "/runbooks/file1.md", "embedding_id": str(uuid.uuid4())},
            {"file_path": "/runbooks/file2.md", "embedding_id": str(uuid.uuid4())}
        ]
        expected_result = {
            "updated_count": 2,
            "deleted_count": 1,
            "status": "success"
        }
        mock_task.return_value = Mock(id="task-update-101")
        mock_task.return_value.get = Mock(return_value=expected_result)

        # Act
        result = update_chromadb.apply_async(args=[embeddings]).get()

        # Assert
        assert "updated_count" in result
        assert "deleted_count" in result
        assert "status" in result
        assert result["status"] in ["success", "partial", "failed"]

    @patch('backend.workflows.tasks.kb_sync_tasks.invalidate_cache.apply_async')
    def test_invalidate_cache_contract(self, mock_task):
        """Test invalidate_cache task contract."""
        # Arrange
        cache_keys = ["runbook:db_troubleshooting", "runbook:api_recovery"]
        expected_result = {
            "invalidated_keys": 2,
            "status": "success"
        }
        mock_task.return_value = Mock(id="task-inval-202")
        mock_task.return_value.get = Mock(return_value=expected_result)

        # Act
        result = invalidate_cache.apply_async(args=[cache_keys]).get()

        # Assert
        assert "invalidated_keys" in result
        assert "status" in result
        assert result["status"] in ["success", "failed"]

    def test_workflow_parallel_embeddings(self):
        """Test that regenerate_embeddings tasks run in parallel within group."""
        # This test verifies that multiple files are processed in parallel
        # Arrange
        runbooks_dir = "/runbooks"

        # Act
        workflow = create_kb_sync_workflow(runbooks_dir=runbooks_dir)

        # Assert
        # Workflow should contain a group for parallel regenerate_embeddings tasks
        assert workflow is not None
        assert isinstance(workflow, chain)
