"""merge usuario column and encuestas tables

Revision ID: 0965a79e7b94
Revises: 20260312_add_encuestas_tables, add_usuario_column
Create Date: 2026-03-13 17:02:54.617233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0965a79e7b94'
down_revision: Union[str, Sequence[str], None] = ('20260312_add_encuestas_tables', 'add_usuario_column')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
