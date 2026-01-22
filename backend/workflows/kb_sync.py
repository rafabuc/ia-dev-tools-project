"""
Knowledge base sync workflow composition.

Workflow chain:
scan_runbooks_dir → detect_changes →
group[regenerate_embeddings tasks] → update_chromadb → invalidate_cache

This workflow synchronizes the knowledge base by detecting file changes,
regenerating embeddings in parallel, updating ChromaDB, and invalidating caches.
"""

from typing import Dict, Any, List
from celery import chain, group, chord

from backend.workflows.tasks.kb_sync_tasks import (
    scan_runbooks_dir,
    detect_changes,
    regenerate_embeddings,
    update_chromadb,
    invalidate_cache,
)
from backend.celery_app import app
from backend.utils.logging import get_logger

logger = get_logger(__name__)


@app.task(bind=True, name="kb_sync.extract_and_process")
def extract_and_process_changes(self, scan_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract files from scan and orchestrate change processing.

    This task bridges scanning and change processing by:
    1. Extracting files from scan result
    2. Detecting changes
    3. Spawning parallel embedding regeneration
    4. Coordinating ChromaDB update and cache invalidation

    Args:
        scan_result: Result from scan_runbooks_dir

    Returns:
        Dict with processing status and metadata
    """
    logger.info("extract_and_process_changes_started")

    # Extract files from scan result
    files = scan_result.get("files", [])
    logger.info(f"Processing {len(files)} files from scan")

    # Detect changes
    changes_result = detect_changes.apply_async(args=[files])
    changes = changes_result.get()

    # Extract changed and deleted files
    changed_files = changes.get("added", []) + changes.get("modified", [])
    deleted_files = changes.get("deleted", [])

    logger.info(
        f"Changes detected: {len(changed_files)} changed, "
        f"{len(deleted_files)} deleted"
    )

    # If no changes, return early
    if not changed_files and not deleted_files:
        logger.info("No changes detected, workflow complete")
        return {
            "status": "no_changes",
            "changes": changes,
            "total_changes": 0
        }

    # Create parallel embedding tasks for changed files
    if changed_files:
        embedding_tasks = group(
            regenerate_embeddings.s(file_path)
            for file_path in changed_files
        )

        # Create a callback task that properly handles the embeddings list
        callback_chain = chain(
            prepare_chromadb_update.s(deleted_files, changed_files),
            invalidate_cache.s()
        )

        # Use chord to wait for all embeddings
        chord_workflow = chord(embedding_tasks, callback_chain)

        # Execute workflow
        result = chord_workflow.apply_async()

        return {
            "status": "processing",
            "changes": changes,
            "workflow_id": str(result.id),
            "changed_files": len(changed_files),
            "deleted_files": len(deleted_files)
        }
    else:
        # Only deletions, no embeddings needed
        update_result = update_chromadb.apply_async(args=[[], deleted_files])
        update_data = update_result.get()

        # Invalidate caches
        cache_keys = [f"runbook:{fp}" for fp in deleted_files]
        invalidate_cache.apply_async(args=[cache_keys])

        return {
            "status": "completed",
            "changes": changes,
            "changed_files": 0,
            "deleted_files": len(deleted_files)
        }


@app.task(bind=True, name="kb_sync.prepare_chromadb_update")
def prepare_chromadb_update(
    self,
    embeddings: List[Dict[str, Any]],
    deleted_files: List[str],
    changed_files: List[str]
) -> List[str]:
    """
    Prepare ChromaDB update and return cache keys for invalidation.

    This task receives embedding results from parallel tasks,
    updates ChromaDB, and returns cache keys for invalidation.

    Args:
        embeddings: List of embedding results from regenerate_embeddings
        deleted_files: List of file paths to delete
        changed_files: List of changed file paths for cache invalidation

    Returns:
        List of cache keys to invalidate
    """
    logger.info(
        f"Preparing ChromaDB update with {len(embeddings)} embeddings, "
        f"{len(deleted_files)} deletions"
    )

    # Call update_chromadb synchronously
    update_result = update_chromadb.apply_async(args=[embeddings, deleted_files])
    chromadb_result = update_result.get()

    logger.info(
        f"ChromaDB updated: {chromadb_result.get('updated_count', 0)} updated, "
        f"{chromadb_result.get('deleted_count', 0)} deleted"
    )

    # Generate cache keys for changed files
    all_affected_files = changed_files + deleted_files
    cache_keys = [f"runbook:{file_path}" for file_path in all_affected_files]

    logger.info(f"Returning {len(cache_keys)} cache keys for invalidation")
    return cache_keys


def create_kb_sync_workflow(runbooks_dir: str) -> chain:
    """
    Create knowledge base synchronization workflow chain.

    Workflow steps:
    1. Scan runbooks directory for all files
    2. Extract files and detect changes
    3. Regenerate embeddings in parallel (within extract_and_process_changes)
    4. Update ChromaDB
    5. Invalidate caches

    Args:
        runbooks_dir: Path to the runbooks directory to scan

    Returns:
        Celery chain object ready for execution

    Example:
        >>> workflow = create_kb_sync_workflow("/app/runbooks")
        >>> result = workflow.apply_async()
        >>> task_id = result.id
    """
    logger.info(f"Creating KB sync workflow for directory: {runbooks_dir}")

    # Create simple chain: scan → extract_and_process
    # The extract_and_process task handles the rest internally
    workflow = chain(
        scan_runbooks_dir.s(runbooks_dir),
        extract_and_process_changes.s()
    )

    logger.info(f"KB sync workflow created for directory: {runbooks_dir}")
    return workflow


def trigger_kb_sync_workflow(runbooks_dir: str) -> str:
    """
    Trigger knowledge base synchronization workflow.

    Args:
        runbooks_dir: Path to the runbooks directory to scan

    Returns:
        Workflow task ID for tracking

    Raises:
        FileNotFoundError: If runbooks directory doesn't exist
    """
    import os

    if not os.path.exists(runbooks_dir):
        raise FileNotFoundError(f"Runbooks directory not found: {runbooks_dir}")

    logger.info(f"Triggering KB sync workflow for directory: {runbooks_dir}")

    workflow = create_kb_sync_workflow(runbooks_dir)
    result = workflow.apply_async()

    task_id = result.id
    logger.info(f"KB sync workflow triggered, task_id={task_id}")

    return task_id


def get_kb_sync_workflow_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of KB sync workflow execution.

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
