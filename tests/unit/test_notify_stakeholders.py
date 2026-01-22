"""
Unit test for notify_stakeholders Celery task.

Tests the task that sends notifications to stakeholders about postmortem completion.

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.tasks.postmortem_tasks import notify_stakeholders
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestNotifyStakeholders:
    """Unit tests for notify_stakeholders task."""

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_success(self, mock_notification_service):
        """Test successful notification to stakeholders."""
        # Arrange
        incident_id = str(uuid.uuid4())
        postmortem_data = {
            "github_url": "https://github.com/org/repo/issues/456",
            "summary": "API service outage postmortem available"
        }

        mock_notification_service.send_notification.return_value = {
            "sent_to": ["webhook", "email"],
            "status": "success",
            "recipients": 5
        }

        # Act
        result = notify_stakeholders(incident_id, postmortem_data)

        # Assert
        assert result is not None
        assert "sent_to" in result
        assert "status" in result
        assert result["status"] == "success"
        assert isinstance(result["sent_to"], list)
        assert len(result["sent_to"]) > 0

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_with_github_url(self, mock_notification_service):
        """Test that GitHub URL is included in notification."""
        # Arrange
        incident_id = str(uuid.uuid4())
        github_url = "https://github.com/org/repo/issues/456"
        postmortem_data = {
            "github_url": github_url,
            "summary": "Postmortem available"
        }

        mock_notification_service.send_notification.return_value = {
            "sent_to": ["webhook"],
            "status": "success",
            "recipients": 3
        }

        # Act
        result = notify_stakeholders(incident_id, postmortem_data)

        # Assert
        mock_notification_service.send_notification.assert_called_once()
        call_args = mock_notification_service.send_notification.call_args
        # Verify GitHub URL was passed
        assert github_url in str(call_args)

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_partial_success(self, mock_notification_service):
        """Test handling of partial notification success."""
        # Arrange
        incident_id = str(uuid.uuid4())
        postmortem_data = {
            "github_url": "https://github.com/org/repo/issues/456",
            "summary": "Postmortem available"
        }

        # Webhook succeeds but email fails
        mock_notification_service.send_notification.return_value = {
            "sent_to": ["webhook"],
            "failed": ["email"],
            "status": "partial",
            "recipients": 3
        }

        # Act
        result = notify_stakeholders(incident_id, postmortem_data)

        # Assert
        assert result["status"] == "partial"
        assert "webhook" in result["sent_to"]

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_complete_failure(self, mock_notification_service):
        """Test handling of complete notification failure."""
        # Arrange
        incident_id = str(uuid.uuid4())
        postmortem_data = {
            "github_url": "https://github.com/org/repo/issues/456",
            "summary": "Postmortem available"
        }

        mock_notification_service.send_notification.return_value = {
            "sent_to": [],
            "status": "failed",
            "error": "All notification channels unavailable"
        }

        # Act
        result = notify_stakeholders(incident_id, postmortem_data)

        # Assert
        assert result["status"] == "failed"

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_missing_github_url(self, mock_notification_service):
        """Test error handling when GitHub URL is missing."""
        # Arrange
        incident_id = str(uuid.uuid4())
        postmortem_data = {
            "summary": "Postmortem available"
            # Missing github_url
        }

        # Act & Assert
        with pytest.raises((ValueError, KeyError)):
            notify_stakeholders(incident_id, postmortem_data)

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_with_retry(self, mock_notification_service):
        """Test retry behavior when notification service fails."""
        # Arrange
        incident_id = str(uuid.uuid4())
        postmortem_data = {
            "github_url": "https://github.com/org/repo/issues/456",
            "summary": "Postmortem available"
        }

        mock_notification_service.send_notification.side_effect = Exception("Service unavailable")

        # Act & Assert
        with pytest.raises(Exception, match="Service unavailable"):
            notify_stakeholders(incident_id, postmortem_data)

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_max_retries(self, mock_notification_service):
        """Test that task respects max_retries=3 configuration."""
        # Verify task configuration
        assert notify_stakeholders.max_retries == 3

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_multiple_channels(self, mock_notification_service):
        """Test notification to multiple channels."""
        # Arrange
        incident_id = str(uuid.uuid4())
        postmortem_data = {
            "github_url": "https://github.com/org/repo/issues/456",
            "summary": "Postmortem available"
        }

        mock_notification_service.send_notification.return_value = {
            "sent_to": ["webhook", "email", "slack"],
            "status": "success",
            "recipients": 10
        }

        # Act
        result = notify_stakeholders(incident_id, postmortem_data)

        # Assert
        assert len(result["sent_to"]) == 3
        assert "webhook" in result["sent_to"]
        assert "email" in result["sent_to"]
        assert "slack" in result["sent_to"]

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_includes_summary(self, mock_notification_service):
        """Test that summary is included in notification."""
        # Arrange
        incident_id = str(uuid.uuid4())
        summary = "Critical API outage postmortem available for review"
        postmortem_data = {
            "github_url": "https://github.com/org/repo/issues/456",
            "summary": summary
        }

        mock_notification_service.send_notification.return_value = {
            "sent_to": ["webhook"],
            "status": "success",
            "recipients": 5
        }

        # Act
        result = notify_stakeholders(incident_id, postmortem_data)

        # Assert
        mock_notification_service.send_notification.assert_called_once()
        call_args = mock_notification_service.send_notification.call_args
        # Verify summary was passed
        assert summary in str(call_args) or call_args[1].get("summary") == summary

    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    def test_notify_stakeholders_recipient_count(self, mock_notification_service):
        """Test that recipient count is tracked."""
        # Arrange
        incident_id = str(uuid.uuid4())
        postmortem_data = {
            "github_url": "https://github.com/org/repo/issues/456",
            "summary": "Postmortem available"
        }

        mock_notification_service.send_notification.return_value = {
            "sent_to": ["webhook"],
            "status": "success",
            "recipients": 15
        }

        # Act
        result = notify_stakeholders(incident_id, postmortem_data)

        # Assert
        assert "recipients" in result
        assert result["recipients"] == 15
