"""create workflows table

Revision ID: 001
Revises:
Create Date: 2025-12-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create workflows table."""
    op.create_table(
        'workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('type', sa.Enum('INCIDENT_RESPONSE', 'POSTMORTEM_PUBLISH', 'KB_SYNC', name='workflow_type'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='workflow_status'), nullable=False),
        sa.Column('triggered_by', sa.String(255), nullable=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
    )

    # Create indexes
    op.create_index('ix_workflows_status_created_at', 'workflows', ['status', 'created_at'])
    op.create_index('ix_workflows_type_status', 'workflows', ['type', 'status'])
    op.create_index('ix_workflows_incident_id', 'workflows', ['incident_id'])


def downgrade() -> None:
    """Drop workflows table."""
    op.drop_index('ix_workflows_incident_id')
    op.drop_index('ix_workflows_type_status')
    op.drop_index('ix_workflows_status_created_at')
    op.drop_table('workflows')
    op.execute('DROP TYPE workflow_status')
    op.execute('DROP TYPE workflow_type')
