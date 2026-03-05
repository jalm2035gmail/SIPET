"""unificar heads

Revision ID: 8d6c7410e0b7
Revises: 20260228_add_ia_config_table, xxx
Create Date: 2026-02-28 19:36:18.807780

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d6c7410e0b7'
down_revision: Union[str, Sequence[str], None] = ('20260228_add_ia_config_table', 'xxx')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
