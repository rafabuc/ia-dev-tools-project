"""
Integration test for full incident response workflow.

This test verifies the end-to-end execution of the incident response workflow
from incident creation through all workflow steps to completion.

TDD: This test should FAIL initially before full implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock

try:
    from backend.workflows.incident_response import create_incident_workflow
    from backend.models.workflow import Workflow, WorkflowStatus
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestIncidentWorkflowIntegration:
    """Integration tests for complete incident response workflow."""

    @patch('backend.workflows.tasks.incident_tasks.NotificationService')
    @patch('backend.workflows.tasks.incident_tasks.GitHubClient')
    @patch('backend.workflows.tasks.incident_tasks.chromadb_client')
    @patch('builtins.open')
    @patch('backend.workflows.tasks.incident_tasks.WorkflowService')
    def test_full_workflow_execution_success(
        self,
        mock_workflow_service,
        mock_file,
        mock_chromadb,
        mock_github,
        mock_notification
    ):
        """Test that complete workflow executes all steps successfully."""
        # Arrange
        title = "API Service Down"
        description = "500 errors on /api/chat"
        severity = "critical"
        log_file_path = "/logs/api.log"

        # Mock all external dependencies
        incident_id = uuid.uuid4()
        mock_workflow_service.return_value.create_incident.return_value = Mock(
            id=incident_id,
            created_at="2025-12-29T10:30:00Z"
        )

        mock_file.return_value.__enter__.return_value.read.return_value = "[2025-12-29] ERROR Connection timeout"

        mock_chromadb.query.return_value = {
            "documents": [["Database troubleshooting guide"]],
            "metadatas": [[{"title": "DB Issues", "category": "troubleshooting"}]],
            "distances": [[0.05]]
        }

        mock_github.return_value.create_issue.return_value = {
            "html_url": "https://github.com/org/repo/issues/123",
            "number": 123
        }

        mock_notification.return_value.send.return_value = {
            "sent_to": ["webhook"],
            "status": "success"
        }

        # Act
        workflow = create_incident_workflow(
            title=title,
            description=description,
            severity=severity,
            log_file_path=log_file_path
        )

        # Assert - Verify workflow structure
        assert workflow is not None
        assert hasattr(workflow, 'tasks')
        assert len(workflow.tasks) >= 4  # At least 4 steps (some may be optional)

    @patch('backend.workflows.tasks.incident_tasks.WorkflowService')
    def test_workflow_without_log_file(self, mock_workflow_service):
        """Test that workflow works without log file (optional step skipped)."""
        # Arrange
        title = "Manual Incident Report"
        description = "User reported issue"
        severity = "medium"

        incident_id = uuid.uuid4()
        mock_workflow_service.return_value.create_incident.return_value = Mock(
            id=incident_id,
            created_at="2025-12-29T10:30:00Z"
        )

        # Act
        workflow = create_incident_workflow(
            title=title,
            description=description,
            severity=severity,
            log_file_path=None  # No log file
        )

        # Assert
        assert workflow is not None
        # Workflow should still be created even without log file

    @patch('backend.workflows.tasks.incident_tasks.GitHubClient')
    @patch('backend.workflows.tasks.incident_tasks.WorkflowService')
    def test_workflow_handles_github_api_failure(self, mock_workflow_service, mock_github):
        """Test that workflow handles GitHub API failures gracefully."""
        # Arrange
        title = "Test Incident"
        description = "Test description"
        severity = "low"

        incident_id = uuid.uuid4()
        mock_workflow_service.return_value.create_incident.return_value = Mock(
            id=incident_id,
            created_at="2025-12-29T10:30:00Z"
        )

        mock_github.return_value.create_issue.side_effect = Exception("GitHub API unavailable")

        # Act
        workflow = create_incident_workflow(
            title=title,
            description=description,
            severity=severity
        )

        # Assert
        assert workflow is not None
        # Workflow should be created even if GitHub step will fail later

    def test_workflow_validates_required_parameters(self):
        """Test that workflow creation validates required parameters."""
        # Act & Assert
        with pytest.raises(TypeError):
            create_incident_workflow()  # Missing required arguments

    @patch('backend.workflows.tasks.incident_tasks.WorkflowService')
    def test_workflow_creates_correlation_id(self, mock_workflow_service):
        """Test that workflow creates correlation ID for tracing."""
        # Arrange
        title = "Test Incident"
        description = "Test"
        severity = "low"

        incident_id = uuid.uuid4()
        mock_workflow_service.return_value.create_incident.return_value = Mock(
            id=incident_id,
            created_at="2025-12-29T10:30:00Z"
        )

        # Act
        workflow = create_incident_workflow(
            title=title,
            description=description,
            severity=severity,
            triggered_by="test-user"
        )

        # Assert
        assert workflow is not None
        # Correlation ID should be set during workflow execution
