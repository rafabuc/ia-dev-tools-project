"""
WorkflowStep SQLAlchemy model for tracking individual steps within workflows.
"""

import uuid
from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, DateTime, Text, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base


class WorkflowStepStatus(str, PyEnum):
    """Enum for workflow step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep(Base):
    """
    WorkflowStep entity for tracking individual step execution within workflow.
    """

    __tablename__ = "workflow_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WorkflowStepStatus] = mapped_column(Enum(WorkflowStepStatus), nullable=False, default=WorkflowStepStatus.PENDING)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    result_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="steps")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("workflow_id", "step_order", name="uq_workflow_step_order"),
        Index("ix_workflow_steps_workflow_id", "workflow_id"),
        Index("ix_workflow_steps_workflow_id_step_order", "workflow_id", "step_order"),
    )

    def __repr__(self) -> str:
        """String representation of WorkflowStep."""
        return f"<WorkflowStep(id={self.id}, workflow_id={self.workflow_id}, step_name={self.step_name}, status={self.status})>"