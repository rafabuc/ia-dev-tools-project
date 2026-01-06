"""
Celery tasks for incident response workflow.

This module implements the five tasks in the incident response chain:
1. create_incident_record - Create incident in database
2. analyze_logs_async - Parse logs and extract error timeline
3. search_related_runbooks - Query vector DB for relevant runbooks
4. create_github_issue - Post to GitHub API with details
5. send_notification - Webhook/email to configured channels
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from celery import Task
from backend.celery_app import app
from backend.utils.logging import get_logger, set_correlation_id, log_workflow_event
from backend.database import SessionLocal
from backend.models.incident import Incident, IncidentSeverity, IncidentStatus
from backend.utils.log_parser import LogParser, LogParseError
from backend.services.embedding_service import embedding_service
from backend.integrations.github_client import GitHubClient, GitHubAPIError
from backend.services.notification_service import NotificationService, NotificationError
#from backend.utils.retry import exponential_backoff_with_jitter

logger = get_logger(__name__)


@app.task(bind=True, max_retries=0, name="workflows.create_incident_record")
def create_incident_record(
    self: Task,
    title: str,
    description: str,
    severity: str,
    log_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create incident record in database.

    Args:
        self: Celery task instance
        title: Incident title
        description: Incident description
        severity: Incident severity level
        log_file_path: Optional path to log file

    Returns:
        Dict[str, Any]: {
            "incident_id": "uuid",
            "created_at": "ISO8601 timestamp"
        }

    Raises:
        DatabaseError: If incident creation fails
    """
    correlation_id = set_correlation_id()
    logger.info("create_incident_record_started", title=title, severity=severity, correlation_id=correlation_id)

    db = SessionLocal()
    try:
        # Create incident in database
        incident = Incident(
            title=title,
            description=description,
            severity=IncidentSeverity[severity.upper()],
            status=IncidentStatus.OPEN
        )

        db.add(incident)
        db.commit()
        db.refresh(incident)

        result = {
            "incident_id": str(incident.id),
            "created_at": incident.created_at.isoformat()
        }

        logger.info("create_incident_record_completed", incident_id=str(incident.id))
        return result

    except Exception as e:
        db.rollback()
        logger.error("create_incident_record_failed", error=str(e))
        raise
    finally:
        db.close()


@app.task(bind=True, max_retries=3, default_retry_delay=1, name="workflows.analyze_logs_async")
def analyze_logs_async(
    self: Task,
    incident_id: str,
    log_file_path: str
) -> Dict[str, Any]:
    """
    Parse log file and extract error timeline.

    Args:
        self: Celery task instance
        incident_id: Incident identifier
        log_file_path: Path to log file

    Returns:
        Dict[str, Any]: {
            "errors_found": int,
            "timeline": [{"timestamp": "...", "level": "...", "message": "..."}],
            "patterns": ["pattern1", "pattern2"]
        }

    Raises:
        FileNotFoundError: If log file missing
        ParseError: If log format unrecognized
    """
    logger.info("analyze_logs_async_started", incident_id=incident_id, log_file=log_file_path)

    try:
        # Parse log file using log parser utility
        parser = LogParser(log_format="standard")
        result = parser.parse_file(log_file_path)

        logger.info("analyze_logs_async_completed", incident_id=incident_id, errors_found=result["errors_found"])
        return result

    except FileNotFoundError as e:
        logger.error("analyze_logs_async_file_not_found", incident_id=incident_id, error=str(e))
        raise
    except LogParseError as e:
        logger.error("analyze_logs_async_parse_error", incident_id=incident_id, error=str(e))
        raise
    except Exception as e:
        logger.error("analyze_logs_async_failed", incident_id=incident_id, error=str(e))
        # Retry with exponential backoff
        raise self.retry(exc=e)


@app.task(bind=True, max_retries=3, default_retry_delay=2, name="workflows.search_related_runbooks")
def search_related_runbooks(
    self: Task,
    incident_id: str,
    error_summary: str,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Query vector DB for relevant runbooks.

    Args:
        self: Celery task instance
        incident_id: Incident identifier
        error_summary: Error summary for semantic search
        limit: Maximum number of runbooks to return

    Returns:
        Dict[str, Any]: {
            "runbooks": [
                {"title": "...", "category": "...", "relevance_score": 0.95},
                ...
            ]
        }

    Raises:
        VectorDBError: If ChromaDB query fails
    """
    logger.info("search_related_runbooks_started", incident_id=incident_id, query=error_summary)

    try:
        # Query ChromaDB for relevant runbooks using embedding service
        similar_docs = embedding_service.search_similar_documents(
            query=error_summary,
            n_results=limit
        )

        # Transform results to match expected format
        runbooks = []
        for doc in similar_docs:
            metadata = doc.get("metadata", {})
            runbooks.append({
                "title": metadata.get("title", "Unknown"),
                "category": metadata.get("category", "general"),
                "relevance_score": 1.0 - doc.get("distance", 1.0)  # Convert distance to similarity score
            })

        result = {
            "runbooks": runbooks
        }

        logger.info("search_related_runbooks_completed", incident_id=incident_id, runbooks_found=len(result["runbooks"]))
        return result

    except Exception as e:
        logger.error("search_related_runbooks_failed", incident_id=incident_id, error=str(e))
        raise self.retry(exc=e)


@app.task(bind=True, max_retries=3, default_retry_delay=4, name="workflows.create_github_issue")
def create_github_issue(
    self: Task,
    incident_id: str,
    title: str,
    body: str,
    labels: List[str] = None
) -> Dict[str, Any]:
    """
    Create tracking issue in GitHub.

    Args:
        self: Celery task instance
        incident_id: Incident identifier
        title: Issue title
        body: Issue body content
        labels: Issue labels (default: ["incident"])

    Returns:
        Dict[str, Any]: {
            "issue_url": "https://github.com/...",
            "issue_number": 123
        }

    Raises:
        GitHubAPIError: If issue creation fails
    """
    if labels is None:
        labels = ["incident"]

    logger.info("create_github_issue_started", incident_id=incident_id, title=title)

    try:
        # Create GitHub issue using GitHub client
        github_client = GitHubClient()
        issue_data = github_client.create_issue(
            title=title,
            body=body,
            labels=labels
        )

        result = {
            "issue_url": issue_data["html_url"],
            "issue_number": issue_data["number"]
        }

        logger.info("create_github_issue_completed", incident_id=incident_id, issue_number=result["issue_number"])
        return result

    except GitHubAPIError as e:
        logger.error("create_github_issue_api_error", incident_id=incident_id, error=str(e))
        raise self.retry(exc=e)
    except Exception as e:
        logger.error("create_github_issue_failed", incident_id=incident_id, error=str(e))
        raise self.retry(exc=e)


@app.task(bind=True, max_retries=3, default_retry_delay=1, name="workflows.send_notification")
def send_notification(
    self: Task,
    incident_id: str,
    message: str,
    channels: List[str] = None
) -> Dict[str, Any]:
    """
    Send notification to configured channels.

    Args:
        self: Celery task instance
        incident_id: Incident identifier
        message: Notification message
        channels: List of channels (default: ["webhook"])

    Returns:
        Dict[str, Any]: {
            "sent_to": ["webhook"],
            "status": "success"
        }

    Raises:
        NotificationError: If all channels fail
    """
    if channels is None:
        channels = ["webhook"]

    logger.info("send_notification_started", incident_id=incident_id, channels=channels)

    try:
        # Send notification using notification service
        notification_service = NotificationService()
        notification_result = notification_service.send(
            message=message,
            channels=channels,
            metadata={"incident_id": incident_id}
        )

        result = {
            "sent_to": notification_result["sent_to"],
            "status": notification_result["status"]
        }

        logger.info("send_notification_completed", incident_id=incident_id, status=result["status"])
        return result

    except NotificationError as e:
        logger.error("send_notification_error", incident_id=incident_id, error=str(e))
        raise self.retry(exc=e)
    except Exception as e:
        logger.error("send_notification_failed", incident_id=incident_id, error=str(e))
        raise self.retry(exc=e)
