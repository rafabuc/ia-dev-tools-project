"""
Celery tasks for postmortem publish workflow.

Tasks:
- generate_postmortem_sections: Generate postmortem content using Claude API
- render_jinja_template: Render postmortem template with sections
- embed_in_chromadb: Embed postmortem document in ChromaDB
- notify_stakeholders: Send notifications about postmortem completion
"""

from typing import Dict, Any, List
import uuid
from datetime import datetime
from celery import Task

from backend.celery_app import app
from backend.database import get_db
from backend.models.incident import Incident
from backend.integrations.claude_client import claude_client
from backend.services.template_service import template_service
from backend.services.embedding_service import embedding_service
#from backend.services.notification_service import notification_service
from backend.utils.logging import get_logger

logger = get_logger(__name__)


@app.task(
    bind=True,
    max_retries=3,
    name="postmortem.generate_sections"
)
def generate_postmortem_sections(
    self: Task,
    incident_id: str
) -> Dict[str, Any]:
    """
    Generate postmortem sections using Claude API.

    Args:
        incident_id: UUID of the resolved incident

    Returns:
        Dict containing postmortem sections:
        - summary: Brief summary of the incident
        - timeline: List of timeline events
        - root_cause: Root cause analysis
        - impact: Impact description
        - resolution: Resolution description
        - lessons_learned: List of lessons learned

    Raises:
        ValueError: If incident not found or not resolved
        Exception: If Claude API fails (will retry)
    """
    logger.info(f"Generating postmortem sections for incident {incident_id}")

    db = next(get_db())
    try:
        # Fetch incident
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            raise ValueError(f"Incident not found: {incident_id}")

        if not incident.resolved_at:
            raise ValueError(f"Incident not resolved: {incident_id}")

        # Prepare context for Claude API
        context = {
            "incident_id": incident_id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "created_at": incident.created_at.isoformat() if incident.created_at else None,
            "resolved_at": incident.resolved_at.isoformat(),
            "duration": str(incident.resolved_at - incident.created_at) if incident.created_at else "unknown",
            "metadata": incident.metadata or {}
        }

        # Generate postmortem using Claude API
        try:
            sections = claude_client.generate_postmortem(context)
        except Exception as exc:
            logger.error(f"Claude API failed for incident {incident_id}: {exc}")
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)

        # Validate response structure
        required_fields = [
            "summary", "timeline", "root_cause",
            "impact", "resolution", "lessons_learned"
        ]
        missing_fields = [f for f in required_fields if f not in sections]
        if missing_fields:
            raise ValueError(f"Missing required fields in Claude response: {missing_fields}")

        # Validate timeline structure
        if not isinstance(sections["timeline"], list):
            raise ValueError("Timeline must be a list")

        # Validate lessons learned structure
        if not isinstance(sections["lessons_learned"], list):
            raise ValueError("Lessons learned must be a list")

        logger.info(f"Successfully generated postmortem sections for incident {incident_id}")
        return sections

    finally:
        db.close()


@app.task(
    bind=True,
    max_retries=0,  # No retries for template rendering (deterministic)
    name="postmortem.render_template"
)
def render_jinja_template(
    self: Task,
    
    sections: Dict[str, Any],
    incident_id: str,
) -> Dict[str, Any]:
    """
    Render postmortem template with generated sections.

    Args:
        incident_id: UUID of the incident
        sections: Postmortem sections from generate_postmortem_sections

    Returns:
        Dict containing:
        - rendered_document: Rendered markdown document
        - format: Document format (always "markdown")

    Raises:
        ValueError: If required fields are missing
        KeyError: If template variables are missing
    """
    print("render_jinja_template Rendering postmortem template for incident", incident_id)
    #print("render_jinja_template Sections:", sections)
    logger.info(f"Rendering postmortem template for incident {incident_id}")

    # Validate required fields
    required_fields = [
        "summary", "timeline", "root_cause",
        "impact", "resolution", "lessons_learned"
    ]
    # TODO RBM
    #missing_fields = [f for f in required_fields if f not in sections]
    #if missing_fields:
    #    raise ValueError(f"Missing required fields: {missing_fields}")

    db = next(get_db())
    try:
        # Fetch incident for additional context
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            raise ValueError(f"Incident not found: {incident_id}")

        # Prepare template context
        template_context = {
            "incident_id": incident_id,
            "incident_title": incident.title,
            "date": incident.created_at.strftime("%Y-%m-%d") if incident.created_at else "Unknown",
            "severity": incident.severity,
            "duration": str(incident.resolved_at - incident.created_at) if incident.created_at and incident.resolved_at else "Unknown",
            "summary": sections.get("summary", ""),
            "timeline": sections.get("timeline", []),
            "root_cause": sections.get("root_cause", ""),
            "impact": sections.get("impact", ""),
            "resolution": sections.get("resolution", ""),
            "lessons_learned": sections.get("lessons_learned", []),
            "action_items": sections.get("action_items", []),
            "generated_at": datetime.now().isoformat(),
            "status": "Published"
        }

        # Render template
        rendered_document = template_service.render_postmortem(template_context)
        #print(f"render_jinja_template Rendered document: {rendered_document}")
        logger.info(f"Successfully rendered postmortem for incident {incident_id}")
        return {
            "rendered_document": rendered_document,
            "format": "markdown"
        }

    finally:
        db.close()


@app.task(
    bind=True,
    max_retries=3,
    name="postmortem.embed_chromadb"
)
def embed_in_chromadb(
    self: Task,
    document: str,
    incident_id: str
   
) -> Dict[str, Any]:
    """
    Embed postmortem document in ChromaDB for searchability.

    Args:
        incident_id: UUID of the incident
        document: Rendered postmortem document

    Returns:
        Dict containing:
        - embedding_id: UUID of the embedding
        - collection: ChromaDB collection name
        - status: "indexed" or "failed"

    Raises:
        ValueError: If document is empty
        Exception: If ChromaDB operation fails (will retry)
    """
    logger.info(f"Embedding postmortem in ChromaDB for incident {incident_id}")
    print(f"Embedding postmortem in ChromaDB for incident {incident_id}")
    print(f"Document: document type: {type(document)}")
    # Validate document
    if not document:#or not document.strip():
        raise ValueError("Cannot embed empty document")

    try:
        # Embed document in ChromaDB
        result = embedding_service.embed_document(
            incident_id=incident_id,
            document=document['rendered_document'],#document,
            metadata={
                "document_type": "postmortem",
                "incident_id": incident_id,
                "indexed_at": datetime.now().isoformat()
            }
        )

        logger.info(f"Successfully embedded postmortem for incident {incident_id}")
        return result

    except Exception as exc:
        logger.error(f"ChromaDB embedding failed for incident {incident_id}: {exc}")
        print(f"ChromaDB embedding failed for incident {incident_id}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@app.task(
    bind=True,
    max_retries=3,
    name="postmortem.notify_stakeholders"
)
def notify_stakeholders(
    self: Task,
    incident_id: str,
    postmortem_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send notifications to stakeholders about postmortem completion.

    Args:
        incident_id: UUID of the incident
        postmortem_data: Dict containing:
            - github_url: URL to GitHub issue
            - summary: Brief summary for notification

    Returns:
        Dict containing:
        - sent_to: List of channels where notifications were sent
        - status: "success", "partial", or "failed"
        - recipients: Number of recipients notified

    Raises:
        ValueError: If required fields are missing
        KeyError: If github_url is missing
        Exception: If notification service fails (will retry)
    """
    logger.info(f"Notifying stakeholders about postmortem for incident {incident_id}")

    print(f"Postmortem data: {postmortem_data} ++++++++++++++")
    # Validate required fields
    #TODO RBM
    '''
    if "github_url" not in postmortem_data:
        raise ValueError("Missing required field: github_url")
    if "summary" not in postmortem_data:
        raise ValueError("Missing required field: summary")
    '''

    try:
        # Send notifications
        notification_payload = {
            "incident_id": incident_id,
            #"github_url": postmortem_data["github_url"],
            #"summary": postmortem_data["summary"],
            "notification_type": "postmortem_published"
        }

        result = notification_payload#None#TODO RBM notification_service.send_notification(notification_payload)

        logger.info(f"Successfully notified stakeholders for incident {incident_id}")
        return result

    except Exception as exc:
        logger.error(f"Notification failed for incident {incident_id}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
