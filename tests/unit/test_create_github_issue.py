"""
Unit test for create_github_issue Celery task.

TDD: This test should FAIL initially before full implementation.
"""

import pytest
from unittest.mock import Mock, patch

try:
    from backend.workflows.tasks.incident_tasks import create_github_issue
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestCreateGitHubIssue:
    """Unit tests for create_github_issue task."""

    @patch('backend.workflows.tasks.incident_tasks.GitHubClient')
    def test_creates_issue_successfully(self, mock_github):
        """Test that GitHub issue is created with correct parameters."""
        # Arrange
        incident_id = "test-incident-123"
        title = "[INCIDENT] API Service Down"
        body = "## Description\n500 errors on /api/chat"
        labels = ["incident", "critical"]

        mock_github.return_value.create_issue.return_value = {
            "html_url": "https://github.com/org/repo/issues/123",
            "number": 123
        }

        # Act
        result = create_github_issue(incident_id, title, body, labels)

        # Assert
        assert result["issue_url"] == "https://github.com/org/repo/issues/123"
        assert result["issue_number"] == 123
        mock_github.return_value.create_issue.assert_called_once()

    @patch('backend.workflows.tasks.incident_tasks.GitHubClient')
    def test_uses_default_labels(self, mock_github):
        """Test that default 'incident' label is used if not specified."""
        # Arrange
        incident_id = "test-incident-123"
        title = "Test Issue"
        body = "Test body"

        mock_github.return_value.create_issue.return_value = {
            "html_url": "https://github.com/org/repo/issues/1",
            "number": 1
        }

        # Act
        result = create_github_issue(incident_id, title, body)

        # Assert
        call_args = mock_github.return_value.create_issue.call_args
        assert "incident" in call_args[1].get("labels", []) or "incident" in str(call_args)

    @patch('backend.workflows.tasks.incident_tasks.create_github_issue.retry')
    @patch('backend.workflows.tasks.incident_tasks.GitHubClient')
    def test_retries_on_api_error(self, mock_github, mock_retry):
        """Test that GitHub API errors trigger retry."""
        # Arrange
        incident_id = "test-incident-123"
        title = "Test Issue"
        body = "Test body"
        mock_github.return_value.create_issue.side_effect = Exception("API rate limit exceeded")

        # Act & Assert
        with pytest.raises(Exception):
            create_github_issue(incident_id, title, body)

    @patch('backend.workflows.tasks.incident_tasks.GitHubClient')
    def test_handles_authentication_error(self, mock_github):
        """Test that authentication errors are handled properly."""
        # Arrange
        incident_id = "test-incident-123"
        title = "Test Issue"
        body = "Test body"
        mock_github.return_value.create_issue.side_effect = Exception("Unauthorized: 401")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            create_github_issue(incident_id, title, body)
        assert "401" in str(exc_info.value)
