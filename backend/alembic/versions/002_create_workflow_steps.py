"""create workflow_steps table

Revision ID: 002
Revises: 001
Create Date: 2025-12-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create workflow_steps table."""
    op.create_table(
        'workflow_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_name', sa.String(255), nullable=False),
        sa.Column('step_order', sa.Integer, nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED', name='workflow_step_status'), nullable=False),
        sa.Column('retry_count', sa.Integer, default=0, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('task_id', sa.String(255), nullable=True),
        sa.Column('result_summary', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('workflow_id', 'step_order', name='uq_workflow_step_order'),
    )

    # Create indexes
    op.create_index('ix_workflow_steps_workflow_id', 'workflow_steps', ['workflow_id'])
    op.create_index('ix_workflow_steps_workflow_id_step_order', 'workflow_steps', ['workflow_id', 'step_order'])


def downgrade() -> None:
    """Drop workflow_steps table."""
    op.drop_index('ix_workflow_steps_workflow_id_step_order')
    op.drop_index('ix_workflow_steps_workflow_id')
    op.drop_table('workflow_steps')
    op.execute('DROP TYPE workflow_step_status')
