"""
Incident response workflow composition.

This module composes the incident response workflow chain:
create_incident_record → analyze_logs_async → search_related_runbooks →
create_github_issue → send_notification
"""

from typing import Optional
from celery import chain

from backend.workflows.tasks.incident_tasks import (
    create_incident_record,
    analyze_logs_async,
    search_related_runbooks,
    create_github_issue,
    send_notification,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def create_incident_workflow(
    title: str,
    description: str,
    severity: str,
    log_file_path: Optional[str] = None,
    triggered_by: Optional[str] = None
):
    """
    Create and return incident response workflow chain.

    This workflow executes the following steps in sequence:
    1. Create incident record in database
    2. Analyze log file asynchronously (if provided)
    3. Search for related runbooks based on incident context
    4. Create GitHub tracking issue
    5. Send notifications to configured channels

    Args:
        title: Incident title
        description: Incident description
        severity: Incident severity level (low, medium, high, critical)
        log_file_path: Optional path to log file for analysis
        triggered_by: Optional user/system identifier who triggered workflow

    Returns:
        celery.chain: Configured workflow chain ready for execution

    Example:
        workflow = create_incident_workflow(
            title="API Service Down",
            description="500 errors on /api/chat",
            severity="critical",
            log_file_path="/logs/api.log"
        )
        result = workflow.apply_async()
    """
    logger.info("creating_incident_workflow", title=title, severity=severity, triggered_by=triggered_by)

    # Compose workflow chain
    workflow = chain(
        # Step 1: Create incident record (no retries - must succeed or fail immediately)
        create_incident_record.si(title, description, severity, log_file_path),

        # Step 2: Analyze logs asynchronously (3 retries with exponential backoff)
        analyze_logs_async.s(log_file_path) if log_file_path else None,

        # Step 3: Search for related runbooks (3 retries)
        search_related_runbooks.s(f"{title} {description}"),

        #TODO RBM
        # Step 4: Create GitHub tracking issue (3 retries)
        #create_github_issue.s(
        #    title=f"[INCIDENT] {title}",
        #    body=f"## Description\n{description}\n\n## Severity\n{severity}"
        #),

        # Step 5: Send notifications (3 retries)
        #send_notification.s(f"Incident workflow completed for: {title}")
    )

    # Filter out None values (for optional steps like analyze_logs)
    workflow.tasks = [task for task in workflow.tasks if task is not None]

    return workflow
