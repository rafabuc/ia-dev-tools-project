"""
FastAPI routes for workflow management.
"""

import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.workflows.incident_response import create_incident_workflow
from backend.workflows.postmortem_publish import trigger_postmortem_workflow
from backend.workflows.kb_sync import trigger_kb_sync_workflow
from backend.services.workflow_service import WorkflowService
from backend.services.workflow_cache import WorkflowCache
from backend.models.workflow import WorkflowStatus, WorkflowType
from backend.utils.logging import get_logger, set_correlation_id

logger = get_logger(__name__)
router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# Request/Response models
class IncidentWorkflowRequest(BaseModel):
    """Request model for incident workflow trigger."""
    title: str = Field(..., description="Incident title", min_length=1, max_length=500)
    description: str = Field(..., description="Incident description", min_length=1)
    severity: str = Field(..., description="Incident severity (low, medium, high, critical)")
    log_file_path: Optional[str] = Field(None, description="Optional path to log file")
    triggered_by: Optional[str] = Field(None, description="User/system identifier")


class WorkflowResponse(BaseModel):
    """Response model for workflow trigger."""
    workflow_id: str = Field(..., description="Unique workflow identifier")
    type: str = Field(..., description="Workflow type")
    status: str = Field(..., description="Current workflow status")
    created_at: str = Field(..., description="Creation timestamp")
    message: str = Field(..., description="Success message")


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status query."""
    workflow_id: str
    type: str
    status: str
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    progress: Optional[str] = None
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    steps: Optional[list] = None
    workflow_data: Optional[Dict[str, Any]] = None  # Añadido


# Dependency injection
def get_db_session():
    """Get database session (placeholder)."""
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/incident/{incident_id}", response_model=WorkflowResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_incident_workflow(
    incident_id: str,
    request: IncidentWorkflowRequest,
    db: Session = Depends(get_db_session)
) -> WorkflowResponse:
    """
    Trigger incident response workflow for an incident.
    """
    correlation_id = set_correlation_id()
    logger.info(
        "trigger_incident_workflow_requested",
        incident_id=incident_id,
        title=request.title,
        severity=request.severity,
        correlation_id=correlation_id
    )

    try:
        # Create workflow service
        workflow_service = WorkflowService(db)

        # Create workflow record in database
        workflow = workflow_service.create_workflow(
            workflow_type=WorkflowType.INCIDENT_RESPONSE,
            triggered_by=request.triggered_by,
            incident_id=uuid.UUID(incident_id),
            workflow_data={  # CAMBIADO: de metadata a workflow_data
                "title": request.title,
                "severity": request.severity,
                "has_log_file": request.log_file_path is not None,
                "description": request.description
            }
        )

        # Create and trigger Celery workflow chain
        celery_workflow = create_incident_workflow(
            title=request.title,
            description=request.description,
            severity=request.severity,
            log_file_path=request.log_file_path,
            triggered_by=request.triggered_by
        )

        # Execute workflow asynchronously
        result = celery_workflow.apply_async()

        # Update workflow with Celery task ID
        workflow_service.update_workflow_data(
            workflow.id,
            {"celery_chain_id": str(result.id)}
        )

        # Cache workflow state for fast retrieval
        cache = WorkflowCache()
        cache.set_workflow_state(
            workflow.id,
            {
                "id": str(workflow.id),
                "type": workflow.type.value,
                "status": workflow.status.value,
                "progress": "0/5 steps completed",
                "current_step": "create_incident_record"
            }
        )

        logger.info(
            "trigger_incident_workflow_success",
            workflow_id=str(workflow.id),
            celery_task_id=str(result.id),
            correlation_id=correlation_id
        )

        return WorkflowResponse(
            workflow_id=str(workflow.id),
            type=workflow.type.value,
            status=workflow.status.value,
            created_at=workflow.created_at.isoformat(),
            message="Incident response workflow triggered successfully"
        )

    except Exception as e:
        logger.error(
            "trigger_incident_workflow_failed",
            incident_id=incident_id,
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger workflow: {str(e)}"
        )


@router.get("/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    db: Session = Depends(get_db_session)
) -> WorkflowStatusResponse:
    """
    Get current status of a workflow.
    """
    logger.info("get_workflow_status_requested", workflow_id=workflow_id)

    try:
        # Try cache first (fast path)
        cache = WorkflowCache()
        cached_state = cache.get_workflow_state(uuid.UUID(workflow_id))

        if cached_state:
            logger.info("get_workflow_status_cache_hit", workflow_id=workflow_id)
            return WorkflowStatusResponse(**cached_state)

        # Cache miss - query database (authoritative)
        workflow_service = WorkflowService(db)
        workflow = workflow_service.get_workflow(uuid.UUID(workflow_id))

        if not workflow:
            logger.warning("get_workflow_status_not_found", workflow_id=workflow_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )

        # Get workflow steps
        steps = workflow_service.get_workflow_steps(workflow.id)
        completed_steps = sum(1 for s in steps if s.status.value == "completed")
        total_steps = len(steps)

        # Build response
        response = WorkflowStatusResponse(
            workflow_id=str(workflow.id),
            type=workflow.type.value,
            status=workflow.status.value,
            created_at=workflow.created_at.isoformat(),
            updated_at=workflow.updated_at.isoformat(),
            completed_at=workflow.completed_at.isoformat() if workflow.completed_at else None,
            progress=f"{completed_steps}/{total_steps} steps completed" if steps else None,
            current_step=next((s.step_name for s in steps if s.status.value == "running"), None),
            error_message=workflow.error_message,
            workflow_data=workflow.workflow_data,  # CAMBIADO
            steps=[
                {
                    "name": s.step_name,
                    "status": s.status.value,
                    "order": s.step_order,
                    "retry_count": s.retry_count
                }
                for s in steps
            ] if steps else None
        )

        # Update cache
        cache.set_workflow_state(
            workflow.id,
            {
                "id": str(workflow.id),
                "type": workflow.type.value,
                "status": workflow.status.value,
                "progress": response.progress,
                "current_step": response.current_step,
                "workflow_data": workflow.workflow_data
            }
        )

        logger.info("get_workflow_status_success", workflow_id=workflow_id, status=workflow.status.value)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_workflow_status_failed", workflow_id=workflow_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve workflow status: {str(e)}"
        )


@router.post("/postmortem/{incident_id}", response_model=WorkflowResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_postmortem(
    incident_id: str,
    db: Session = Depends(get_db_session)
) -> WorkflowResponse:
    """
    Trigger automated postmortem generation and publishing workflow.

    Workflow steps:
    1. Generate postmortem sections using Claude API
    2. Render Jinja2 template
    3. Parallel execution:
       - Create GitHub issue
       - Embed in ChromaDB
    4. Notify stakeholders

    Note: Incident must be resolved before triggering postmortem workflow.
    """
    correlation_id = set_correlation_id()
    logger.info(
        "trigger_postmortem_workflow_requested",
        incident_id=incident_id,
        correlation_id=correlation_id
    )

    try:
        # Validate UUID
        incident_uuid = uuid.UUID(incident_id)

        # Create workflow service
        workflow_service = WorkflowService(db)

        # Create workflow record in database
        workflow = workflow_service.create_workflow(
            workflow_type=WorkflowType.POSTMORTEM_PUBLISH,
            triggered_by="api",
            incident_id=incident_uuid,
            workflow_data={
                "incident_id": incident_id,
                "workflow_type": "postmortem"
            }
        )

        # Trigger Celery workflow
        task_id = trigger_postmortem_workflow(incident_id)

        # Update workflow with Celery task ID
        workflow_service.update_workflow_data(
            workflow.id,
            {"celery_chain_id": task_id}
        )

        # Cache workflow state for fast retrieval
        cache = WorkflowCache()
        cache.set_workflow_state(
            workflow.id,
            {
                "id": str(workflow.id),
                "type": workflow.type.value,
                "status": workflow.status.value,
                "progress": "0/4 steps completed",
                "current_step": "generate_postmortem_sections"
            }
        )

        logger.info(
            "trigger_postmortem_workflow_success",
            workflow_id=str(workflow.id),
            celery_task_id=task_id,
            correlation_id=correlation_id
        )

        return WorkflowResponse(
            workflow_id=str(workflow.id),
            type=workflow.type.value,
            status=workflow.status.value,
            created_at=workflow.created_at.isoformat(),
            message="Postmortem publish workflow triggered successfully"
        )

    except ValueError as exc:
        logger.error(
            "trigger_postmortem_workflow_validation_failed",
            incident_id=incident_id,
            error=str(exc),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        logger.error(
            "trigger_postmortem_workflow_failed",
            incident_id=incident_id,
            error=str(exc),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger postmortem workflow: {str(exc)}"
        )


class KBSyncRequest(BaseModel):
    """Request model for KB sync workflow trigger."""
    runbooks_dir: str = Field(..., description="Path to runbooks directory to scan")
    triggered_by: Optional[str] = Field(None, description="User/system identifier")


@router.post("/kb-sync", response_model=WorkflowResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_kb_sync(
    request: KBSyncRequest,
    db: Session = Depends(get_db_session)
) -> WorkflowResponse:
    """
    Trigger knowledge base synchronization workflow.

    Workflow steps:
    1. Scan runbooks directory for all files
    2. Detect changes (added/modified/deleted)
    3. Regenerate embeddings in parallel for changed files
    4. Batch update ChromaDB
    5. Invalidate caches

    Note: Only one KB sync can run at a time (concurrency lock).
    """
    correlation_id = set_correlation_id()
    logger.info(
        "trigger_kb_sync_workflow_requested",
        runbooks_dir=request.runbooks_dir,
        correlation_id=correlation_id
    )

    # Acquire lock to prevent concurrent KB sync operations
    cache = WorkflowCache()
    lock = cache.acquire_lock("kb_sync", timeout_seconds=600, blocking_timeout=0)

    if not lock:
        logger.warning(
            "trigger_kb_sync_workflow_locked",
            runbooks_dir=request.runbooks_dir,
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="KB sync workflow is already running. Please wait for it to complete."
        )

    try:
        # Create workflow service
        workflow_service = WorkflowService(db)

        # Create workflow record in database
        workflow = workflow_service.create_workflow(
            workflow_type=WorkflowType.KB_SYNC,
            triggered_by=request.triggered_by or "api",
            workflow_data={
                "runbooks_dir": request.runbooks_dir,
                "workflow_type": "kb_sync"
            }
        )

        # Trigger Celery workflow
        task_id = trigger_kb_sync_workflow(request.runbooks_dir)

        # Update workflow with Celery task ID and lock info
        workflow_service.update_workflow_data(
            workflow.id,
            {
                "celery_chain_id": task_id,
                "has_lock": True,
                "lock_acquired_at": correlation_id
            }
        )

        # Cache workflow state for fast retrieval
        cache.set_workflow_state(
            workflow.id,
            {
                "id": str(workflow.id),
                "type": workflow.type.value,
                "status": workflow.status.value,
                "progress": "0/5 steps completed",
                "current_step": "scan_runbooks_dir"
            }
        )

        logger.info(
            "trigger_kb_sync_workflow_success",
            workflow_id=str(workflow.id),
            celery_task_id=task_id,
            correlation_id=correlation_id
        )

        # Note: Lock will be released automatically after timeout (600s)
        # or when workflow completes via a callback mechanism
        # For now, we rely on the timeout mechanism

        return WorkflowResponse(
            workflow_id=str(workflow.id),
            type=workflow.type.value,
            status=workflow.status.value,
            created_at=workflow.created_at.isoformat(),
            message="Knowledge base sync workflow triggered successfully"
        )

    except FileNotFoundError as exc:
        # Release lock on error
        cache.release_lock(lock)
        logger.error(
            "trigger_kb_sync_workflow_validation_failed",
            runbooks_dir=request.runbooks_dir,
            error=str(exc),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        # Release lock on error
        cache.release_lock(lock)
        logger.error(
            "trigger_kb_sync_workflow_failed",
            runbooks_dir=request.runbooks_dir,
            error=str(exc),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger KB sync workflow: {str(exc)}"
        )