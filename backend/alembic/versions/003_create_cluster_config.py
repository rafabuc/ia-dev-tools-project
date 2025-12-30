"""create cluster_config table

Revision ID: 003
Revises: 002
Create Date: 2025-12-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create cluster_config table."""
    op.create_table(
        'cluster_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), unique=True, nullable=False),
        sa.Column('kubeconfig_path', sa.String(512), nullable=False),
        sa.Column('default_namespace', sa.String(255), default='default', nullable=False),
        sa.Column('timeout_seconds', sa.Integer, default=30, nullable=False),
        sa.Column('is_active', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )

    # Create index
    op.create_index('ix_cluster_config_is_active', 'cluster_config', ['is_active'])


def downgrade() -> None:
    """Drop cluster_config table."""
    op.drop_index('ix_cluster_config_is_active')
    op.drop_table('cluster_config')
