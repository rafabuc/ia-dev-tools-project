"""change enum values to uppercase

Revision ID: 006
Revises: 005
Create Date: 2025-12-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cambiar valores del enum workflow_type a mayúsculas
    '''
    op.execute("ALTER TYPE workflow_type RENAME VALUE 'incident_response' TO 'INCIDENT_RESPONSE'")
    op.execute("ALTER TYPE workflow_type RENAME VALUE 'postmortem_publish' TO 'POSTMORTEM_PUBLISH'")
    op.execute("ALTER TYPE workflow_type RENAME VALUE 'kb_sync' TO 'KB_SYNC'")
    
    # Cambiar valores del enum workflow_status a mayúsculas
    op.execute("ALTER TYPE workflow_status RENAME VALUE 'pending' TO 'PENDING'")
    op.execute("ALTER TYPE workflow_status RENAME VALUE 'running' TO 'RUNNING'")
    op.execute("ALTER TYPE workflow_status RENAME VALUE 'completed' TO 'COMPLETED'")
    op.execute("ALTER TYPE workflow_status RENAME VALUE 'failed' TO 'FAILED'")
    
    # Cambiar valores del enum workflow_step_status a mayúsculas
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'pending' TO 'PENDING'")
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'running' TO 'RUNNING'")
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'completed' TO 'COMPLETED'")
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'failed' TO 'FAILED'")
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'skipped' TO 'SKIPPED'")
    '''
    pass


def downgrade() -> None:
    # Revertir cambios (volver a minúsculas)
    '''
    op.execute("ALTER TYPE workflow_type RENAME VALUE 'INCIDENT_RESPONSE' TO 'incident_response'")
    op.execute("ALTER TYPE workflow_type RENAME VALUE 'POSTMORTEM_PUBLISH' TO 'postmortem_publish'")
    op.execute("ALTER TYPE workflow_type RENAME VALUE 'KB_SYNC' TO 'kb_sync'")
    
    op.execute("ALTER TYPE workflow_status RENAME VALUE 'PENDING' TO 'pending'")
    op.execute("ALTER TYPE workflow_status RENAME VALUE 'RUNNING' TO 'running'")
    op.execute("ALTER TYPE workflow_status RENAME VALUE 'COMPLETED' TO 'completed'")
    op.execute("ALTER TYPE workflow_status RENAME VALUE 'FAILED' TO 'failed'")
    
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'PENDING' TO 'pending'")
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'RUNNING' TO 'running'")
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'COMPLETED' TO 'completed'")
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'FAILED' TO 'failed'")
    op.execute("ALTER TYPE workflow_step_status RENAME VALUE 'SKIPPED' TO 'skipped'")
    '''
    pass