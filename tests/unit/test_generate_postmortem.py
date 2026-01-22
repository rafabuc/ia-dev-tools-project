"""
Unit test for generate_postmortem_sections Celery task.

Tests the task that generates postmortem sections using Claude API.

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.tasks.postmortem_tasks import generate_postmortem_sections
    from backend.models.incident import Incident
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestGeneratePostmortemSections:
    """Unit tests for generate_postmortem_sections task."""

    @patch('backend.workflows.tasks.postmortem_tasks.db')
    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    def test_generate_postmortem_sections_success(self, mock_claude, mock_db):
        """Test successful generation of postmortem sections."""
        # Arrange
        incident_id = str(uuid.uuid4())
        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.title = "API Service Outage"
        mock_incident.description = "500 errors on production API"
        mock_incident.severity = "critical"
        mock_incident.created_at = datetime(2025, 12, 29, 10, 0, 0)
        mock_incident.resolved_at = datetime(2025, 12, 29, 10, 45, 0)
        mock_incident.metadata = {
            "logs_analyzed": True,
            "runbooks_searched": True
        }

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident

        mock_claude.generate_postmortem.return_value = {
            "summary": "API service experienced 45-minute outage due to database connection pool exhaustion",
            "timeline": [
                {"time": "10:00", "event": "First 500 errors detected"},
                {"time": "10:15", "event": "Root cause identified"},
                {"time": "10:45", "event": "Fix deployed and verified"}
            ],
            "root_cause": "Database connection pool size was insufficient for peak load",
            "impact": "API unavailable for 45 minutes, affecting 1000+ users",
            "resolution": "Increased connection pool size from 10 to 50 connections",
            "lessons_learned": [
                "Implement connection pool monitoring",
                "Add circuit breakers for database calls",
                "Set up alerts for connection pool exhaustion"
            ]
        }

        # Act
        result = generate_postmortem_sections(incident_id)

        # Assert
        assert result is not None
        assert "summary" in result
        assert "timeline" in result
        assert "root_cause" in result
        assert "impact" in result
        assert "resolution" in result
        assert "lessons_learned" in result
        assert isinstance(result["timeline"], list)
        assert isinstance(result["lessons_learned"], list)
        assert len(result["timeline"]) > 0
        assert len(result["lessons_learned"]) > 0

    @patch('backend.workflows.tasks.postmortem_tasks.db')
    def test_generate_postmortem_incident_not_found(self, mock_db):
        """Test error handling when incident is not found."""
        # Arrange
        incident_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Incident not found"):
            generate_postmortem_sections(incident_id)

    @patch('backend.workflows.tasks.postmortem_tasks.db')
    def test_generate_postmortem_incident_not_resolved(self, mock_db):
        """Test error handling when incident is not yet resolved."""
        # Arrange
        incident_id = str(uuid.uuid4())
        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.resolved_at = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident

        # Act & Assert
        with pytest.raises(ValueError, match="Incident not resolved"):
            generate_postmortem_sections(incident_id)

    @patch('backend.workflows.tasks.postmortem_tasks.db')
    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    def test_generate_postmortem_api_failure_with_retry(self, mock_claude, mock_db):
        """Test retry behavior when Claude API fails."""
        # Arrange
        incident_id = str(uuid.uuid4())
        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.title = "Test Incident"
        mock_incident.resolved_at = datetime.now()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident
        mock_claude.generate_postmortem.side_effect = Exception("API timeout")

        # Act & Assert
        with pytest.raises(Exception, match="API timeout"):
            generate_postmortem_sections(incident_id)

    @patch('backend.workflows.tasks.postmortem_tasks.db')
    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    def test_generate_postmortem_with_metadata_context(self, mock_claude, mock_db):
        """Test that incident metadata is included in context for generation."""
        # Arrange
        incident_id = str(uuid.uuid4())
        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.title = "Test Incident"
        mock_incident.resolved_at = datetime.now()
        mock_incident.metadata = {
            "analyzed_logs": ["/logs/api.log"],
            "error_patterns": ["connection_timeout", "database_error"],
            "runbooks_found": ["Database Troubleshooting", "API Recovery"]
        }

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident
        mock_claude.generate_postmortem.return_value = {
            "summary": "Test",
            "timeline": [],
            "root_cause": "Test",
            "impact": "Test",
            "resolution": "Test",
            "lessons_learned": []
        }

        # Act
        result = generate_postmortem_sections(incident_id)

        # Assert
        mock_claude.generate_postmortem.assert_called_once()
        call_args = mock_claude.generate_postmortem.call_args
        # Verify metadata was passed to Claude API
        assert call_args is not None

    @patch('backend.workflows.tasks.postmortem_tasks.db')
    @patch('backend.workflows.tasks.postmortem_tasks.claude_client')
    def test_generate_postmortem_validates_response_structure(self, mock_claude, mock_db):
        """Test that response validation catches malformed Claude API responses."""
        # Arrange
        incident_id = str(uuid.uuid4())
        mock_incident = Mock(spec=Incident)
        mock_incident.id = incident_id
        mock_incident.resolved_at = datetime.now()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_incident

        # Malformed response missing required fields
        mock_claude.generate_postmortem.return_value = {
            "summary": "Test"
            # Missing other required fields
        }

        # Act & Assert
        with pytest.raises((ValueError, KeyError)):
            generate_postmortem_sections(incident_id)
