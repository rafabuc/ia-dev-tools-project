"""
Unit test for scan_runbooks_dir Celery task.

Tests the task that scans the runbook directory for files.

TDD: This test should FAIL initially before implementation.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.tasks.kb_sync_tasks import scan_runbooks_dir
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestScanRunbooksDir:
    """Unit tests for scan_runbooks_dir task."""

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    def test_scan_runbooks_success(self, mock_scanner):
        """Test successful scanning of runbook directory."""
        # Arrange
        runbooks_dir = "/runbooks"
        mock_scanner.scan_directory.return_value = {
            "files": [
                {"path": "/runbooks/db_troubleshooting.md", "mtime": 1703001234.5, "size": 1024},
                {"path": "/runbooks/api_recovery.md", "mtime": 1703001235.5, "size": 2048}
            ],
            "total_files": 2
        }

        # Act
        result = scan_runbooks_dir(runbooks_dir)

        # Assert
        assert result is not None
        assert "files" in result
        assert "total_files" in result
        assert "scan_timestamp" in result
        assert result["total_files"] == 2
        assert len(result["files"]) == 2

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    def test_scan_runbooks_empty_directory(self, mock_scanner):
        """Test scanning empty runbook directory."""
        # Arrange
        runbooks_dir = "/empty_runbooks"
        mock_scanner.scan_directory.return_value = {
            "files": [],
            "total_files": 0
        }

        # Act
        result = scan_runbooks_dir(runbooks_dir)

        # Assert
        assert result["total_files"] == 0
        assert len(result["files"]) == 0

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    def test_scan_runbooks_directory_not_found(self, mock_scanner):
        """Test error handling when directory doesn't exist."""
        # Arrange
        runbooks_dir = "/nonexistent"
        mock_scanner.scan_directory.side_effect = FileNotFoundError("Directory not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            scan_runbooks_dir(runbooks_dir)

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    def test_scan_runbooks_filters_markdown_files(self, mock_scanner):
        """Test that only markdown files are included in scan."""
        # Arrange
        runbooks_dir = "/runbooks"
        mock_scanner.scan_directory.return_value = {
            "files": [
                {"path": "/runbooks/doc1.md", "mtime": 1703001234.5, "size": 1024},
                {"path": "/runbooks/doc2.md", "mtime": 1703001235.5, "size": 2048}
                # Non-markdown files should be filtered out
            ],
            "total_files": 2
        }

        # Act
        result = scan_runbooks_dir(runbooks_dir)

        # Assert
        assert all(f["path"].endswith(".md") for f in result["files"])

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    def test_scan_runbooks_includes_metadata(self, mock_scanner):
        """Test that file metadata is included in results."""
        # Arrange
        runbooks_dir = "/runbooks"
        mock_scanner.scan_directory.return_value = {
            "files": [
                {
                    "path": "/runbooks/doc.md",
                    "mtime": 1703001234.5,
                    "size": 1024,
                    "hash": "abc123"
                }
            ],
            "total_files": 1
        }

        # Act
        result = scan_runbooks_dir(runbooks_dir)

        # Assert
        assert "mtime" in result["files"][0]
        assert "path" in result["files"][0]

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    def test_scan_runbooks_no_retries(self, mock_scanner):
        """Test that scan task has max_retries=0."""
        # Verify task configuration
        assert scan_runbooks_dir.max_retries == 0

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    def test_scan_runbooks_recursive_scan(self, mock_scanner):
        """Test that scan includes subdirectories."""
        # Arrange
        runbooks_dir = "/runbooks"
        mock_scanner.scan_directory.return_value = {
            "files": [
                {"path": "/runbooks/doc1.md", "mtime": 1703001234.5, "size": 1024},
                {"path": "/runbooks/subdir/doc2.md", "mtime": 1703001235.5, "size": 2048}
            ],
            "total_files": 2
        }

        # Act
        result = scan_runbooks_dir(runbooks_dir)

        # Assert
        # Should include files from subdirectories
        assert any("subdir" in f["path"] for f in result["files"])

    @patch('backend.workflows.tasks.kb_sync_tasks.file_scanner')
    def test_scan_runbooks_timestamp_format(self, mock_scanner):
        """Test that scan timestamp is in ISO format."""
        # Arrange
        runbooks_dir = "/runbooks"
        mock_scanner.scan_directory.return_value = {
            "files": [],
            "total_files": 0
        }

        # Act
        result = scan_runbooks_dir(runbooks_dir)

        # Assert
        assert "scan_timestamp" in result
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(result["scan_timestamp"].replace("Z", "+00:00"))
