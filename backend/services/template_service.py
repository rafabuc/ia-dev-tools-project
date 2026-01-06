"""
Jinja2 template rendering service for postmortems.

Provides template rendering capabilities with error handling and validation.
"""

from typing import Dict, Any
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

from backend.utils.logging import get_logger

logger = get_logger(__name__)


class TemplateService:
    """Service for rendering Jinja2 templates."""

    def __init__(self, templates_dir: str = None):
        """
        Initialize template service.

        Args:
            templates_dir: Path to templates directory
                          (defaults to backend/templates)
        """
        if templates_dir is None:
            # Default to backend/templates
            backend_dir = Path(__file__).parent.parent
            templates_dir = str(backend_dir / "templates")

        if not os.path.exists(templates_dir):
            raise ValueError(f"Templates directory not found: {templates_dir}")

        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=False,  # Markdown doesn't need HTML escaping
            trim_blocks=True,
            lstrip_blocks=True
        )

        logger.info(f"Template service initialized with dir: {templates_dir}")

    def render_postmortem(self, context: Dict[str, Any]) -> str:
        """
        Render postmortem template with provided context.

        Args:
            context: Template context containing:
                - incident_id: Incident UUID
                - incident_title: Incident title
                - date: Incident date
                - severity: Incident severity
                - duration: Incident duration
                - summary: Postmortem summary
                - timeline: List of timeline events
                - root_cause: Root cause analysis
                - impact: Impact description
                - resolution: Resolution description
                - lessons_learned: List of lessons learned
                - action_items: Optional list of action items
                - generated_at: Generation timestamp
                - status: Document status

        Returns:
            Rendered markdown document

        Raises:
            TemplateNotFound: If template file not found
            ValueError: If required context variables missing
        """
        logger.info(f"Rendering postmortem template for incident {context.get('incident_id')}")

        # Validate required fields
        required_fields = [
            "incident_id", "incident_title", "summary",
            "timeline", "root_cause", "impact",
            "resolution", "lessons_learned"
        ]
        missing_fields = [f for f in required_fields if f not in context]
        if missing_fields:
            raise ValueError(f"Missing required template variables: {missing_fields}")

        # Validate timeline structure
        if not isinstance(context["timeline"], list):
            raise ValueError("Timeline must be a list")

        # Validate lessons learned structure
        if not isinstance(context["lessons_learned"], list):
            raise ValueError("Lessons learned must be a list")

        try:
            # Load template
            template = self.env.get_template("postmortem.md.j2")

            # Render template
            rendered = template.render(**context)

            logger.info(
                f"Successfully rendered postmortem ({len(rendered)} chars) "
                f"for incident {context['incident_id']}"
            )

            return rendered

        except TemplateNotFound as exc:
            logger.error(f"Template not found: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Template rendering failed: {exc}")
            raise

    def render_custom_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Render a custom template with provided context.

        Args:
            template_name: Name of template file (e.g., "custom.md.j2")
            context: Template context variables

        Returns:
            Rendered document

        Raises:
            TemplateNotFound: If template file not found
        """
        logger.info(f"Rendering custom template: {template_name}")

        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)

            logger.info(f"Successfully rendered {template_name} ({len(rendered)} chars)")
            return rendered

        except TemplateNotFound as exc:
            logger.error(f"Template not found: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Template rendering failed: {exc}")
            raise

    def render_string(self, template_str: str, context: Dict[str, Any]) -> str:
        """
        Render a template from string.

        Args:
            template_str: Template string
            context: Template context variables

        Returns:
            Rendered document
        """
        logger.info("Rendering template from string")

        try:
            template = Template(template_str)
            rendered = template.render(**context)

            logger.info(f"Successfully rendered template string ({len(rendered)} chars)")
            return rendered

        except Exception as exc:
            logger.error(f"Template rendering failed: {exc}")
            raise

    def list_templates(self) -> list:
        """
        List available templates.

        Returns:
            List of template filenames
        """
        templates = self.env.list_templates()
        logger.info(f"Found {len(templates)} templates")
        return templates


# Global template service instance
template_service = TemplateService()
