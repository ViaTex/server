"""merge heads

Revision ID: c6ba0a089662
Revises: 2b3c4d5e6f7a, 5c8a9d0e1f2a
Create Date: 2026-03-20 12:16:01.552133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6ba0a089662'
down_revision: Union[str, None] = ('2b3c4d5e6f7a', '5c8a9d0e1f2a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
