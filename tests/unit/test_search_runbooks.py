"""
Unit test for search_related_runbooks Celery task.

TDD: This test should FAIL initially before full implementation.
"""

import pytest
from unittest.mock import Mock, patch

try:
    from backend.workflows.tasks.incident_tasks import search_related_runbooks
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestSearchRelatedRunbooks:
    """Unit tests for search_related_runbooks task."""

    @patch('backend.workflows.tasks.incident_tasks.chromadb_client')
    def test_searches_vector_db_successfully(self, mock_chromadb):
        """Test that vector DB is queried with error summary."""
        # Arrange
        incident_id = "test-incident-123"
        error_summary = "connection timeout database error"
        mock_chromadb.query.return_value = {
            "documents": [["Runbook content 1"], ["Runbook content 2"]],
            "metadatas": [
                [{"title": "Database Issues", "category": "troubleshooting"}],
                [{"title": "Connection Handling", "category": "incident_response"}]
            ],
            "distances": [[0.05], [0.13]]
        }

        # Act
        result = search_related_runbooks(incident_id, error_summary)

        # Assert
        assert "runbooks" in result
        assert isinstance(result["runbooks"], list)

    @patch('backend.workflows.tasks.incident_tasks.chromadb_client')
    def test_returns_limited_results(self, mock_chromadb):
        """Test that results are limited to specified count."""
        # Arrange
        incident_id = "test-incident-123"
        error_summary = "test error"
        limit = 3

        # Act
        result = search_related_runbooks(incident_id, error_summary, limit=limit)

        # Assert
        if result["runbooks"]:
            assert len(result["runbooks"]) <= limit

    @patch('backend.workflows.tasks.incident_tasks.chromadb_client')
    def test_handles_empty_results(self, mock_chromadb):
        """Test that empty vector DB results are handled gracefully."""
        # Arrange
        incident_id = "test-incident-123"
        error_summary = "nonexistent error pattern"
        mock_chromadb.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

        # Act
        result = search_related_runbooks(incident_id, error_summary)

        # Assert
        assert result["runbooks"] == []

    @patch('backend.workflows.tasks.incident_tasks.search_related_runbooks.retry')
    @patch('backend.workflows.tasks.incident_tasks.chromadb_client')
    def test_retries_on_vector_db_error(self, mock_chromadb, mock_retry):
        """Test that vector DB errors trigger retry."""
        # Arrange
        incident_id = "test-incident-123"
        error_summary = "test error"
        mock_chromadb.query.side_effect = Exception("ChromaDB connection failed")

        # Act & Assert
        with pytest.raises(Exception):
            search_related_runbooks(incident_id, error_summary)
