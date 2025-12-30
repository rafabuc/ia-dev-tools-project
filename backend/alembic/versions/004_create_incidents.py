"""create incidents table

Revision ID: 004
Revises: 003
Create Date: 2025-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create incidents table."""
    op.create_table(
        'incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='incident_severity'), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED', name='incident_status'), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_workflow_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('postmortem_workflow_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['response_workflow_id'], ['workflows.id'], ),
        sa.ForeignKeyConstraint(['postmortem_workflow_id'], ['workflows.id'], ),
    )

    # Create indexes
    op.create_index('ix_incidents_severity_status', 'incidents', ['severity', 'status'])
    op.create_index('ix_incidents_response_workflow_id', 'incidents', ['response_workflow_id'])
    op.create_index('ix_incidents_postmortem_workflow_id', 'incidents', ['postmortem_workflow_id'])


def downgrade() -> None:
    """Drop incidents table."""
    op.drop_index('ix_incidents_postmortem_workflow_id')
    op.drop_index('ix_incidents_response_workflow_id')
    op.drop_index('ix_incidents_severity_status')
    op.drop_table('incidents')
    op.execute('DROP TYPE incident_status')
    op.execute('DROP TYPE incident_severity')