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
    render_task = render_jinja_template.s(incident_id)

    # Step 3: Parallel execution - create GitHub issue and embed in ChromaDB
    # Both tasks receive the rendered document from step 2
    def create_parallel_tasks(render_result: Dict[str, Any]) -> group:
        """Create parallel tasks for GitHub issue and ChromaDB embedding."""
        rendered_document = render_result["rendered_document"]

        # Create GitHub issue task
        # TODO RBM: 
        '''
        github_task = create_github_issue.s(
            incident_id=incident_id,
            title=f"Postmortem: Incident {incident_id[:8]}",
            body=rendered_document
        )
        '''
        # Embed in ChromaDB task
        chromadb_task = embed_in_chromadb.s(
            incident_id=incident_id,
            document=rendered_document
        )

        return group([ chromadb_task])#github_task

    # Step 4: Notify stakeholders (receives results from parallel tasks)
    def create_notify_task(parallel_results: list) -> notify_stakeholders:
        """
        Create notification task with data from parallel execution.

        Args:
            parallel_results: List containing [github_result, chromadb_result]
        """
        github_result = parallel_results[0]
        chromadb_result = parallel_results[1]

        postmortem_data = {
            "github_url": github_result["issue_url"],
            "summary": f"Postmortem published for incident {incident_id}"
        }

        return notify_stakeholders.s(incident_id, postmortem_data)

    # Compose the workflow chain
    # Note: We use a simpler chain structure that Celery can handle
    workflow = chain(
        generate_task,
        render_task,
        # For parallel execution, we'll use a chord structure
        # chord waits for all tasks in the group to complete before calling callback
        group(
            create_github_issue.s(incident_id, f"Postmortem: Incident {incident_id[:8]}", None),
            embed_in_chromadb.s(incident_id, None)
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
