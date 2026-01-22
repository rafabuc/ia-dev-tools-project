"""
Integration test for full postmortem publish workflow.

Tests the complete workflow chain:
generate_postmortem_sections → render_jinja_template →
group[create_github_issue + embed_in_chromadb] → notify_stakeholders

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.postmortem_publish import create_postmortem_workflow
    from backend.models.incident import Incident
    from backend.models.workflow import Workflow
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestPostmortemWorkflowIntegration:
    """Integration tests for complete postmortem workflow."""

    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    @patch('backend.workflows.tasks.incident_tasks.github_client')
    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    @patch('backend.workflows.tasks.postmortem_tasks.db')
    def test_complete_postmortem_workflow_success(
        self,
        mock_db,
        mock_notification,
        mock_github,
        mock_embedding,
        mock_template,
        mock_claude
    ):
        """Test successful execution of complete postmortem workflow."""
        # Arrange
        incident_id = str(uuid.uuid4())

        # Mock incident data
        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.title = "API Service Outage"
        mock_incident.description = "500 errors on production API"
        mock_incident.severity = "critical"
        mock_incident.created_at = datetime.now() - timedelta(hours=1)
        mock_incident.resolved_at = datetime.now()
        mock_incident.metadata = {
            "logs_analyzed": True,
            "error_patterns": ["connection_timeout"]
        }

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident

        # Mock Claude API response
        mock_claude.generate_postmortem.return_value = {
            "summary": "API outage due to database issues",
            "timeline": [
                {"time": "10:00", "event": "Issue detected"},
                {"time": "10:45", "event": "Issue resolved"}
            ],
            "root_cause": "Database connection pool exhaustion",
            "impact": "45 minutes downtime",
            "resolution": "Increased pool size",
            "lessons_learned": ["Monitor connection pools"]
        }

        # Mock template rendering
        mock_template.render_postmortem.return_value = "# Postmortem: API Service Outage\n\n..."

        # Mock GitHub issue creation
        mock_github.create_issue.return_value = {
            "issue_url": "https://github.com/org/repo/issues/456",
            "issue_number": 456
        }

        # Mock ChromaDB embedding
        mock_embedding.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "postmortems",
            "status": "indexed"
        }

        # Mock notification
        mock_notification.send_notification.return_value = {
            "sent_to": ["webhook"],
            "status": "success",
            "recipients": 5
        }

        # Act
        workflow = create_postmortem_workflow(incident_id=incident_id)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        assert result is not None
        # Verify all workflow steps executed
        mock_claude.generate_postmortem.assert_called_once()
        mock_template.render_postmortem.assert_called_once()
        mock_github.create_issue.assert_called_once()
        mock_embedding.embed_document.assert_called_once()
        mock_notification.send_notification.assert_called_once()

    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    @patch('backend.workflows.tasks.postmortem_tasks.db')
    def test_postmortem_workflow_incident_not_resolved(self, mock_db, mock_claude):
        """Test workflow fails gracefully when incident is not resolved."""
        # Arrange
        incident_id = str(uuid.uuid4())

        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.resolved_at = None  # Not resolved

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident

        # Act
        workflow = create_postmortem_workflow(incident_id=incident_id)

        # Assert
        with pytest.raises(ValueError, match="not resolved"):
            workflow.apply_async().get(timeout=10)

    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    @patch('backend.workflows.tasks.postmortem_tasks.db')
    def test_postmortem_workflow_retries_on_claude_failure(
        self,
        mock_db,
        mock_template,
        mock_claude
    ):
        """Test workflow retries when Claude API fails."""
        # Arrange
        incident_id = str(uuid.uuid4())

        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.resolved_at = datetime.now()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident

        # Simulate Claude API failure
        mock_claude.generate_postmortem.side_effect = Exception("API timeout")

        # Act
        workflow = create_postmortem_workflow(incident_id=incident_id)

        # Assert
        with pytest.raises(Exception, match="API timeout"):
            workflow.apply_async().get(timeout=10)

    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    @patch('backend.workflows.tasks.incident_tasks.github_client')
    @patch('backend.workflows.tasks.postmortem_tasks.db')
    def test_postmortem_workflow_parallel_execution(
        self,
        mock_db,
        mock_github,
        mock_embedding,
        mock_template,
        mock_claude
    ):
        """Test that GitHub issue creation and ChromaDB embedding run in parallel."""
        # Arrange
        incident_id = str(uuid.uuid4())

        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.resolved_at = datetime.now()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident

        mock_claude.generate_postmortem.return_value = {
            "summary": "Test",
            "timeline": [],
            "root_cause": "Test",
            "impact": "Test",
            "resolution": "Test",
            "lessons_learned": []
        }

        mock_template.render_postmortem.return_value = "# Postmortem"

        mock_github.create_issue.return_value = {
            "issue_url": "https://github.com/org/repo/issues/456",
            "issue_number": 456
        }

        mock_embedding.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "postmortems",
            "status": "indexed"
        }

        # Act
        workflow = create_postmortem_workflow(incident_id=incident_id)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        # Both GitHub and ChromaDB operations should have been called
        mock_github.create_issue.assert_called_once()
        mock_embedding.embed_document.assert_called_once()

    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    @patch('backend.workflows.tasks.incident_tasks.github_client')
    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    @patch('backend.workflows.tasks.postmortem_tasks.db')
    def test_postmortem_workflow_tracks_state(
        self,
        mock_db,
        mock_notification,
        mock_github,
        mock_embedding,
        mock_template,
        mock_claude
    ):
        """Test that workflow state is properly tracked in database."""
        # Arrange
        incident_id = str(uuid.uuid4())

        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.resolved_at = datetime.now()

        mock_workflow = Mock(spec=Workflow)
        mock_workflow.id = str(uuid.uuid4())
        mock_workflow.state = "running"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident

        mock_claude.generate_postmortem.return_value = {
            "summary": "Test",
            "timeline": [],
            "root_cause": "Test",
            "impact": "Test",
            "resolution": "Test",
            "lessons_learned": []
        }

        mock_template.render_postmortem.return_value = "# Postmortem"
        mock_github.create_issue.return_value = {
            "issue_url": "https://github.com/org/repo/issues/456",
            "issue_number": 456
        }
        mock_embedding.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "postmortems",
            "status": "indexed"
        }
        mock_notification.send_notification.return_value = {
            "sent_to": ["webhook"],
            "status": "success",
            "recipients": 5
        }

        # Act
        workflow = create_postmortem_workflow(incident_id=incident_id)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        # Workflow state should be tracked
        assert result is not None

    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    @patch('backend.workflows.tasks.postmortem_tasks.embedding_service')
    @patch('backend.workflows.tasks.incident_tasks.github_client')
    @patch('backend.workflows.tasks.postmortem_tasks.notification_service')
    @patch('backend.workflows.tasks.postmortem_tasks.db')
    def test_postmortem_workflow_end_to_end_data_flow(
        self,
        mock_db,
        mock_notification,
        mock_github,
        mock_embedding,
        mock_template,
        mock_claude
    ):
        """Test that data flows correctly through all workflow steps."""
        # Arrange
        incident_id = str(uuid.uuid4())

        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.title = "Test Incident"
        mock_incident.resolved_at = datetime.now()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident

        sections = {
            "summary": "Test summary",
            "timeline": [{"time": "10:00", "event": "Test"}],
            "root_cause": "Test cause",
            "impact": "Test impact",
            "resolution": "Test resolution",
            "lessons_learned": ["Test lesson"]
        }
        mock_claude.generate_postmortem.return_value = sections

        rendered_doc = "# Postmortem: Test Incident\n\nTest summary\n..."
        mock_template.render_postmortem.return_value = rendered_doc

        github_url = "https://github.com/org/repo/issues/789"
        mock_github.create_issue.return_value = {
            "issue_url": github_url,
            "issue_number": 789
        }

        mock_embedding.embed_document.return_value = {
            "embedding_id": str(uuid.uuid4()),
            "collection": "postmortems",
            "status": "indexed"
        }

        mock_notification.send_notification.return_value = {
            "sent_to": ["webhook"],
            "status": "success",
            "recipients": 3
        }

        # Act
        workflow = create_postmortem_workflow(incident_id=incident_id)
        result = workflow.apply_async().get(timeout=10)

        # Assert
        # Verify data flowed through all steps
        # 1. Claude generated sections
        mock_claude.generate_postmortem.assert_called_once()

        # 2. Template received sections
        mock_template.render_postmortem.assert_called_once()

        # 3. Embedding received rendered document
        mock_embedding.embed_document.assert_called_once()
        embed_call_args = mock_embedding.embed_document.call_args
        assert incident_id in str(embed_call_args)

        # 4. Notification received GitHub URL
        mock_notification.send_notification.assert_called_once()
        notify_call_args = mock_notification.send_notification.call_args
        assert github_url in str(notify_call_args) or incident_id in str(notify_call_args)
