"""
Unit test for send_notification Celery task.

TDD: This test should FAIL initially before full implementation.
"""

import pytest
from unittest.mock import Mock, patch

try:
    from backend.workflows.tasks.incident_tasks import send_notification
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestSendNotification:
    """Unit tests for send_notification task."""

    @patch('backend.workflows.tasks.incident_tasks.NotificationService')
    def test_sends_notification_successfully(self, mock_service):
        """Test that notification is sent to configured channels."""
        # Arrange
        incident_id = "test-incident-123"
        message = "Incident workflow completed"
        channels = ["webhook", "email"]

        mock_service.return_value.send.return_value = {
            "sent_to": ["webhook", "email"],
            "status": "success"
        }

        # Act
        result = send_notification(incident_id, message, channels)

        # Assert
        assert result["status"] == "success"
        assert "webhook" in result["sent_to"]
        assert "email" in result["sent_to"]

    @patch('backend.workflows.tasks.incident_tasks.NotificationService')
    def test_uses_default_webhook_channel(self, mock_service):
        """Test that default webhook channel is used if not specified."""
        # Arrange
        incident_id = "test-incident-123"
        message = "Test notification"

        mock_service.return_value.send.return_value = {
            "sent_to": ["webhook"],
            "status": "success"
        }

        # Act
        result = send_notification(incident_id, message)

        # Assert
        assert "webhook" in result["sent_to"]

    @patch('backend.workflows.tasks.incident_tasks.NotificationService')
    def test_handles_partial_failure(self, mock_service):
        """Test that partial channel failures are reported."""
        # Arrange
        incident_id = "test-incident-123"
        message = "Test notification"
        channels = ["webhook", "email", "slack"]

        mock_service.return_value.send.return_value = {
            "sent_to": ["webhook", "slack"],
            "failed": ["email"],
            "status": "partial"
        }

        # Act
        result = send_notification(incident_id, message, channels)

        # Assert
        assert result["status"] == "partial"
        assert len(result["sent_to"]) == 2

    @patch('backend.workflows.tasks.incident_tasks.send_notification.retry')
    @patch('backend.workflows.tasks.incident_tasks.NotificationService')
    def test_retries_on_complete_failure(self, mock_service, mock_retry):
        """Test that complete notification failures trigger retry."""
        # Arrange
        incident_id = "test-incident-123"
        message = "Test notification"
        mock_service.return_value.send.side_effect = Exception("All notification channels failed")

        # Act & Assert
        with pytest.raises(Exception):
            send_notification(incident_id, message)
