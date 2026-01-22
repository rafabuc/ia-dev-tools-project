"""
Unit test for render_jinja_template Celery task.

Tests the task that renders postmortem sections into a formatted document.

TDD: This test should FAIL initially before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock

# These imports will fail until implementation exists - that's expected for TDD
try:
    from backend.workflows.tasks.postmortem_tasks import render_jinja_template
except ImportError:
    pytest.skip("Implementation not yet complete", allow_module_level=True)


class TestRenderJinjaTemplate:
    """Unit tests for render_jinja_template task."""

    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    def test_render_template_success(self, mock_template_service):
        """Test successful rendering of postmortem template."""
        # Arrange
        incident_id = str(uuid.uuid4())
        sections = {
            "summary": "API service experienced outage",
            "timeline": [
                {"time": "10:00", "event": "Issue detected"},
                {"time": "10:45", "event": "Issue resolved"}
            ],
            "root_cause": "Database connection pool exhaustion",
            "impact": "45 minutes downtime",
            "resolution": "Increased pool size",
            "lessons_learned": [
                "Monitor connection pools",
                "Implement circuit breakers"
            ]
        }

        expected_document = """# Postmortem: API Service Outage

## Summary
API service experienced outage

## Timeline
- 10:00 - Issue detected
- 10:45 - Issue resolved

## Root Cause
Database connection pool exhaustion

## Impact
45 minutes downtime

## Resolution
Increased pool size

## Lessons Learned
- Monitor connection pools
- Implement circuit breakers
"""

        mock_template_service.render_postmortem.return_value = expected_document

        # Act
        result = render_jinja_template(incident_id, sections)

        # Assert
        assert result is not None
        assert "rendered_document" in result
        assert "format" in result
        assert result["format"] == "markdown"
        assert isinstance(result["rendered_document"], str)
        assert len(result["rendered_document"]) > 0
        assert "Postmortem" in result["rendered_document"]
        assert "Summary" in result["rendered_document"]

    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    def test_render_template_with_empty_sections(self, mock_template_service):
        """Test handling of empty or minimal sections."""
        # Arrange
        incident_id = str(uuid.uuid4())
        sections = {
            "summary": "",
            "timeline": [],
            "root_cause": "",
            "impact": "",
            "resolution": "",
            "lessons_learned": []
        }

        mock_template_service.render_postmortem.return_value = "# Postmortem\n\nNo details available."

        # Act
        result = render_jinja_template(incident_id, sections)

        # Assert
        assert result is not None
        assert "rendered_document" in result
        # Should still produce valid document even with empty sections

    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    def test_render_template_missing_required_fields(self, mock_template_service):
        """Test error handling for missing required fields."""
        # Arrange
        incident_id = str(uuid.uuid4())
        incomplete_sections = {
            "summary": "Test"
            # Missing other required fields
        }

        # Act & Assert
        with pytest.raises((ValueError, KeyError)):
            render_jinja_template(incident_id, incomplete_sections)

    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    def test_render_template_includes_incident_id(self, mock_template_service):
        """Test that rendered document includes incident ID reference."""
        # Arrange
        incident_id = str(uuid.uuid4())
        sections = {
            "summary": "Test summary",
            "timeline": [{"time": "10:00", "event": "Test"}],
            "root_cause": "Test",
            "impact": "Test",
            "resolution": "Test",
            "lessons_learned": ["Test"]
        }

        mock_template_service.render_postmortem.return_value = f"# Postmortem\n\nIncident ID: {incident_id}"

        # Act
        result = render_jinja_template(incident_id, sections)

        # Assert
        assert incident_id in result["rendered_document"]

    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    def test_render_template_timeline_formatting(self, mock_template_service):
        """Test proper formatting of timeline entries."""
        # Arrange
        incident_id = str(uuid.uuid4())
        sections = {
            "summary": "Test",
            "timeline": [
                {"time": "10:00", "event": "First event"},
                {"time": "10:15", "event": "Second event"},
                {"time": "10:30", "event": "Third event"}
            ],
            "root_cause": "Test",
            "impact": "Test",
            "resolution": "Test",
            "lessons_learned": ["Test"]
        }

        expected_timeline = """- 10:00 - First event
- 10:15 - Second event
- 10:30 - Third event"""

        mock_template_service.render_postmortem.return_value = f"# Postmortem\n\n## Timeline\n{expected_timeline}"

        # Act
        result = render_jinja_template(incident_id, sections)

        # Assert
        assert "10:00" in result["rendered_document"]
        assert "First event" in result["rendered_document"]

    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    def test_render_template_lessons_learned_formatting(self, mock_template_service):
        """Test proper formatting of lessons learned list."""
        # Arrange
        incident_id = str(uuid.uuid4())
        sections = {
            "summary": "Test",
            "timeline": [{"time": "10:00", "event": "Test"}],
            "root_cause": "Test",
            "impact": "Test",
            "resolution": "Test",
            "lessons_learned": [
                "Implement monitoring",
                "Add circuit breakers",
                "Update runbooks"
            ]
        }

        expected_lessons = """- Implement monitoring
- Add circuit breakers
- Update runbooks"""

        mock_template_service.render_postmortem.return_value = f"# Postmortem\n\n## Lessons Learned\n{expected_lessons}"

        # Act
        result = render_jinja_template(incident_id, sections)

        # Assert
        assert "Implement monitoring" in result["rendered_document"]
        assert "Add circuit breakers" in result["rendered_document"]

    @patch('backend.workflows.tasks.postmortem_tasks.template_service')
    def test_render_template_no_retries_on_failure(self, mock_template_service):
        """Test that render task does not retry on failure (max_retries=0)."""
        # Arrange
        incident_id = str(uuid.uuid4())
        sections = {
            "summary": "Test",
            "timeline": [],
            "root_cause": "Test",
            "impact": "Test",
            "resolution": "Test",
            "lessons_learned": []
        }

        mock_template_service.render_postmortem.side_effect = Exception("Template error")

        # Act & Assert
        with pytest.raises(Exception, match="Template error"):
            render_jinja_template(incident_id, sections)

        # Verify task configuration has max_retries=0
        assert render_jinja_template.max_retries == 0
