"""
ClusterConfig SQLAlchemy model for Kubernetes cluster connection settings.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.models.base import Base


class ClusterConfig(Base):
    """
    ClusterConfig entity for storing Kubernetes cluster connection settings.
    """

    __tablename__ = "cluster_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    kubeconfig_path: Mapped[str] = mapped_column(String(512), nullable=False)
    default_namespace: Mapped[str] = mapped_column(String(255), default="default", nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("ix_cluster_config_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        """String representation of ClusterConfig."""
        return f"<ClusterConfig(id={self.id}, name={self.name}, is_active={self.is_active})>"