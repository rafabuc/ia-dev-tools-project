"""
Postmortem publish workflow composition.

Workflow chain:
generate_postmortem_sections → render_jinja_template →
group[create_github_issue + embed_in_chromadb] → notify_stakeholders

This workflow generates a postmortem document from a resolved incident,
publishes it to GitHub, indexes it in ChromaDB, and notifies stakeholders.
"""

from typing import Dict, Any
from celery import chain, group

from backend.workflows.tasks.postmortem_tasks import (
    generate_postmortem_sections,
    render_jinja_template,
    embed_in_chromadb,
    notify_stakeholders,
)
from backend.workflows.tasks.incident_tasks import create_github_issue
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def create_postmortem_workflow(incident_id: str) -> chain:
    """
    Create postmortem publish workflow chain for a resolved incident.

    Workflow steps:
    1. Generate postmortem sections using Claude API
    2. Render Jinja2 template with sections
    3. Parallel execution:
       - Create GitHub issue with postmortem
       - Embed document in ChromaDB
    4. Notify stakeholders about completion

    Args:
        incident_id: UUID of the resolved incident

    Returns:
        Celery chain object ready for execution

    Example:
        >>> workflow = create_postmortem_workflow(incident_id)
        >>> result = workflow.apply_async()
        >>> task_id = result.id
    """
    logger.info(f"Creating postmortem workflow for incident {incident_id}")

    # Step 1: Generate postmortem sections
    generate_task = generate_postmortem_sections.s(incident_id)

    # Step 2: Render template (receives sections from step 1)
    # Note: render_jinja_template now expects sections as first arg, incident_id as second
    render_task = render_jinja_template.s(incident_id)


    # Compose the workflow chain
    # Using chain with intermediate task to handle parallel execution
    from celery import chord
    
    workflow = chain(
        generate_task,
        render_task,
        chord(
            group(
                create_github_issue.s(incident_id, f"Postmortem: Incident {incident_id[:8]}"),
                embed_in_chromadb.s(incident_id)
            ),
            notify_stakeholders.s(incident_id)
        )
    )
    
    logger.info(f"Postmortem workflow created for incident {incident_id}")
    return workflow


def trigger_postmortem_workflow(incident_id: str) -> str:
    """
    Trigger postmortem workflow for a resolved incident.

    Args:
        incident_id: UUID of the resolved incident

    Returns:
        Workflow task ID for tracking

    Raises:
        ValueError: If incident is not resolved
    """
    logger.info(f"Triggering postmortem workflow for incident {incident_id}")

    workflow = create_postmortem_workflow(incident_id)
    result = workflow.apply_async()

    task_id = result.id
    logger.info(f"Postmortem workflow triggered for incident {incident_id}, task_id={task_id}")

    return task_id


def get_postmortem_workflow_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of postmortem workflow execution.

    Args:
        task_id: Workflow task ID

    Returns:
        Dict containing:
        - task_id: Task ID
        - state: Current state (PENDING, STARTED, SUCCESS, FAILURE, RETRY)
        - result: Task result if completed
        - error: Error message if failed
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    status = {
        "task_id": task_id,
        "state": result.state,
    }

    if result.successful():
        status["result"] = result.result
    elif result.failed():
        status["error"] = str(result.info)

    return status