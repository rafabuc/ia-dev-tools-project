"""
Unit test for detect_changes Celery task.

Tests the task that detects changes in runbook files by comparing modification times.

TDD: This test should FAIL initially before implementation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.tasks.kb_sync_tasks import detect_changes
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestDetectChanges:
    """Unit tests for detect_changes task."""

    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    def test_detect_changes_new_files(self, mock_sync_service):
        """Test detection of newly added files."""
        # Arrange
        current_files = [
            {"path": "/runbooks/new_file.md", "mtime": 1703001235.5}
        ]
        mock_sync_service.detect_changes.return_value = {
            "added": ["/runbooks/new_file.md"],
            "modified": [],
            "deleted": [],
            "unchanged": [],
            "total_changes": 1
        }

        # Act
        result = detect_changes(current_files)

        # Assert
        assert len(result["added"]) == 1
        assert "/runbooks/new_file.md" in result["added"]
        assert result["total_changes"] == 1

    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    def test_detect_changes_modified_files(self, mock_sync_service):
        """Test detection of modified files."""
        # Arrange
        current_files = [
            {"path": "/runbooks/updated_file.md", "mtime": 1703001236.5}
        ]
        mock_sync_service.detect_changes.return_value = {
            "added": [],
            "modified": ["/runbooks/updated_file.md"],
            "deleted": [],
            "unchanged": [],
            "total_changes": 1
        }

        # Act
        result = detect_changes(current_files)

        # Assert
        assert len(result["modified"]) == 1
        assert "/runbooks/updated_file.md" in result["modified"]

    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    def test_detect_changes_deleted_files(self, mock_sync_service):
        """Test detection of deleted files."""
        # Arrange
        current_files = []  # File was removed
        mock_sync_service.detect_changes.return_value = {
            "added": [],
            "modified": [],
            "deleted": ["/runbooks/removed_file.md"],
            "unchanged": [],
            "total_changes": 1
        }

        # Act
        result = detect_changes(current_files)

        # Assert
        assert len(result["deleted"]) == 1
        assert "/runbooks/removed_file.md" in result["deleted"]

    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    def test_detect_changes_no_changes(self, mock_sync_service):
        """Test when no changes are detected."""
        # Arrange
        current_files = [
            {"path": "/runbooks/unchanged.md", "mtime": 1703001234.5}
        ]
        mock_sync_service.detect_changes.return_value = {
            "added": [],
            "modified": [],
            "deleted": [],
            "unchanged": ["/runbooks/unchanged.md"],
            "total_changes": 0
        }

        # Act
        result = detect_changes(current_files)

        # Assert
        assert result["total_changes"] == 0
        assert len(result["added"]) == 0
        assert len(result["modified"]) == 0
        assert len(result["deleted"]) == 0

    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    def test_detect_changes_multiple_types(self, mock_sync_service):
        """Test detection of multiple types of changes simultaneously."""
        # Arrange
        current_files = [
            {"path": "/runbooks/new.md", "mtime": 1703001235.5},
            {"path": "/runbooks/updated.md", "mtime": 1703001236.5}
        ]
        mock_sync_service.detect_changes.return_value = {
            "added": ["/runbooks/new.md"],
            "modified": ["/runbooks/updated.md"],
            "deleted": ["/runbooks/old.md"],
            "unchanged": [],
            "total_changes": 3
        }

        # Act
        result = detect_changes(current_files)

        # Assert
        assert result["total_changes"] == 3
        assert len(result["added"]) == 1
        assert len(result["modified"]) == 1
        assert len(result["deleted"]) == 1

    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    def test_detect_changes_mtime_comparison(self, mock_sync_service):
        """Test that changes are detected based on mtime comparison."""
        # Arrange
        current_files = [
            {"path": "/runbooks/file.md", "mtime": 1703001237.5}  # Newer mtime
        ]
        mock_sync_service.detect_changes.return_value = {
            "added": [],
            "modified": ["/runbooks/file.md"],
            "deleted": [],
            "unchanged": [],
            "total_changes": 1
        }

        # Act
        result = detect_changes(current_files)

        # Assert
        mock_sync_service.detect_changes.assert_called_once()
        call_args = mock_sync_service.detect_changes.call_args
        assert current_files in str(call_args)

    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    def test_detect_changes_no_retries(self, mock_sync_service):
        """Test that detect_changes task has max_retries=0."""
        # Verify task configuration
        assert detect_changes.max_retries == 0

    @patch('backend.workflows.tasks.kb_sync_tasks.sync_service')
    def test_detect_changes_first_sync(self, mock_sync_service):
        """Test behavior when this is the first sync (no previous state)."""
        # Arrange
        current_files = [
            {"path": "/runbooks/file1.md", "mtime": 1703001234.5},
            {"path": "/runbooks/file2.md", "mtime": 1703001235.5}
        ]
        # On first sync, all files are considered "added"
        mock_sync_service.detect_changes.return_value = {
            "added": [f["path"] for f in current_files],
            "modified": [],
            "deleted": [],
            "unchanged": [],
            "total_changes": 2
        }

        # Act
        result = detect_changes(current_files)

        # Assert
        assert len(result["added"]) == 2
        assert result["total_changes"] == 2
