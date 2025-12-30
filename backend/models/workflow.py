"""
Workflow data models.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.models.base import Base  # Asegúrate de usar la misma Base
import sqlalchemy as sa

class WorkflowType(str, Enum):
    """Types of workflows."""
    INCIDENT_RESPONSE = "INCIDENT_RESPONSE"
    POSTMORTEM_PUBLISH = "POSTMORTEM_PUBLISH"
    KB_SYNC = "KB_SYNC"


class WorkflowStatus(str, Enum):
    """Workflow status states."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Workflow(Base):
    """Workflow entity."""
    
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(SQLEnum(WorkflowType), nullable=False)
    status = Column(SQLEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.PENDING)
    triggered_by = Column(String(255), nullable=True)
    incident_id = Column(UUID(as_uuid=True), nullable=True)
    
    # NOTA: Después de la migración 005, esta columna será workflow_data
    # Pero temporalmente, mantenla como metadata para que coincida con la DB actual
    workflow_data = Column(JSON, nullable=False, default=dict)
    
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Workflow(id={self.id}, type={self.type}, status={self.status})>"