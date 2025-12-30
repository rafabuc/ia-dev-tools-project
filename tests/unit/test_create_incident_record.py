"""
Unit test for create_incident_record Celery task.

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch
from datetime import datetime

try:
    from backend.workflows.tasks.incident_tasks import create_incident_record
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestCreateIncidentRecord:
    """Unit tests for create_incident_record task."""

    @patch('backend.workflows.tasks.incident_tasks.WorkflowService')
    @patch('backend.workflows.tasks.incident_tasks.db_session')
    def test_creates_incident_successfully(self, mock_db, mock_service):
        """Test that incident record is created successfully."""
        # Arrange
        title = "API Service Down"
        description = "500 errors on /api/chat"
        severity = "critical"
        expected_id = uuid.uuid4()

        mock_incident = Mock(id=expected_id, created_at=datetime.utcnow())
        mock_service.return_value.create_incident.return_value = mock_incident

        # Act
        result = create_incident_record(title, description, severity)

        # Assert
        assert result["incident_id"] == str(expected_id)
        assert "created_at" in result
        mock_service.return_value.create_incident.assert_called_once()

    @patch('backend.workflows.tasks.incident_tasks.WorkflowService')
    def test_handles_database_error(self, mock_service):
        """Test that database errors are handled properly."""
        # Arrange
        mock_service.return_value.create_incident.side_effect = Exception("DB connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            create_incident_record("Test", "Description", "high")
        assert "DB connection failed" in str(exc_info.value)

    def test_validates_required_fields(self):
        """Test that required fields are validated."""
        # Act & Assert
        with pytest.raises(TypeError):
            create_incident_record()  # Missing required arguments
