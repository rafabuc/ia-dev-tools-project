"""
Workflow service for CRUD operations and state transitions.

This service manages workflow entities, handles state transitions,
and provides query methods for workflow tracking.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.models.workflow import Workflow, WorkflowType, WorkflowStatus
from backend.models.workflow_step import WorkflowStep, WorkflowStepStatus


class WorkflowService:
    """Service for managing workflows and workflow steps."""

    def __init__(self, db_session: Session):
        """
        Initialize workflow service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def create_workflow(
        self,
        workflow_type: WorkflowType,
        triggered_by: Optional[str] = None,
        incident_id: Optional[uuid.UUID] = None,
        workflow_data: Optional[Dict[str, Any]] = None  # CAMBIADO: de metadata a workflow_data
    ) -> Workflow:
        """
        Create a new workflow.

        Args:
            workflow_type: Type of workflow (incident_response, postmortem_publish, kb_sync)
            triggered_by: User/system identifier who triggered the workflow
            incident_id: Optional link to incident
            workflow_data: Optional workflow-specific data

        Returns:
            Workflow: Created workflow entity

        Raises:
            SQLAlchemyError: If database operation fails
        """
        workflow = Workflow(
            id=uuid.uuid4(),
            type=workflow_type,
            status=WorkflowStatus.PENDING,
            triggered_by=triggered_by,
            incident_id=incident_id,
            workflow_data=workflow_data or {}  # CAMBIADO
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def get_workflow(self, workflow_id: uuid.UUID) -> Optional[Workflow]:
        """
        Get workflow by ID.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Optional[Workflow]: Workflow entity or None if not found
        """
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def update_workflow_status(
        self,
        workflow_id: uuid.UUID,
        status: WorkflowStatus,
        error_message: Optional[str] = None
    ) -> Workflow:
        """
        Update workflow status.

        Args:
            workflow_id: Workflow identifier
            status: New status
            error_message: Optional error message if failed

        Returns:
            Workflow: Updated workflow entity

        Raises:
            ValueError: If workflow not found
            SQLAlchemyError: If database operation fails
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow.status = status
        workflow.updated_at = datetime.utcnow()

        if status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
            workflow.completed_at = datetime.utcnow()

        if error_message:
            workflow.error_message = error_message

        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def create_workflow_step(
        self,
        workflow_id: uuid.UUID,
        step_name: str,
        step_order: int,
        task_id: Optional[str] = None
    ) -> WorkflowStep:
        """
        Create a workflow step.

        Args:
            workflow_id: Parent workflow ID
            step_name: Step identifier (e.g., 'analyze_logs_async')
            step_order: Execution sequence (1, 2, 3...)
            task_id: Optional Celery task ID

        Returns:
            WorkflowStep: Created workflow step entity

        Raises:
            SQLAlchemyError: If database operation fails
        """
        step = WorkflowStep(
            id=uuid.uuid4(),
            workflow_id=workflow_id,
            step_name=step_name,
            step_order=step_order,
            status=WorkflowStepStatus.PENDING,
            task_id=task_id
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def update_workflow_step_status(
        self,
        step_id: uuid.UUID,
        status: WorkflowStepStatus,
        result_summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> WorkflowStep:
        """
        Update workflow step status.

        Args:
            step_id: Workflow step identifier
            status: New status
            result_summary: Optional result summary
            error_message: Optional error message if failed

        Returns:
            WorkflowStep: Updated workflow step entity

        Raises:
            ValueError: If step not found
            SQLAlchemyError: If database operation fails
        """
        step = self.db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if not step:
            raise ValueError(f"Workflow step {step_id} not found")

        step.status = status

        if status == WorkflowStepStatus.RUNNING:
            step.started_at = datetime.utcnow()

        if status in (WorkflowStepStatus.COMPLETED, WorkflowStepStatus.FAILED, WorkflowStepStatus.SKIPPED):
            step.completed_at = datetime.utcnow()

        if result_summary:
            step.result_summary = result_summary

        if error_message:
            step.error_message = error_message

        self.db.commit()
        self.db.refresh(step)
        return step

    def update_workflow_data(
        self,
        workflow_id: uuid.UUID,
        data: Dict[str, Any]
    ) -> Workflow:
        """
        Update workflow data.

        Args:
            workflow_id: Workflow identifier
            data: Data to merge with existing workflow_data

        Returns:
            Workflow: Updated workflow entity
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow.workflow_data = {**workflow.workflow_data, **data}
        workflow.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def get_workflow_steps(self, workflow_id: uuid.UUID) -> List[WorkflowStep]:
        """
        Get all steps for a workflow, ordered by step_order.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List[WorkflowStep]: List of workflow steps
        """
        return (
            self.db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == workflow_id)
            .order_by(WorkflowStep.step_order)
            .all()
        )
