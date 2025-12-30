"""rename metadata to workflow_data

Revision ID: 005
Revises: 004
Create Date: 2025-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename column metadata to workflow_data in workflows table."""
    # Renombrar la columna metadata a workflow_data
    op.alter_column('workflows', 'metadata', new_column_name='workflow_data', existing_type=postgresql.JSONB)
    
    # Si la columna workflow_data no es nullable=False como en el modelo, ajustarla
    op.alter_column('workflows', 'workflow_data', nullable=False, server_default='{}')


def downgrade() -> None:
    """Rename column workflow_data back to metadata."""
    op.alter_column('workflows', 'workflow_data', new_column_name='metadata', existing_type=postgresql.JSONB)
    op.alter_column('workflows', 'metadata', nullable=True)