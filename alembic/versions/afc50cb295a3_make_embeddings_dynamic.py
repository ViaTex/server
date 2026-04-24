"""make_embeddings_dynamic

Revision ID: afc50cb295a3
Revises: m3n4o5p6q7r8
Create Date: 2026-04-24 15:43:08.136298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afc50cb295a3'
down_revision: Union[str, None] = 'm3n4o5p6q7r8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Clear the old 384-d data so new dimensions don't conflict
    op.execute("UPDATE exam_responses SET question_embedding = NULL, response_embedding = NULL;")

    # 2. Change columns to dynamic vector type
    op.execute("""
        ALTER TABLE exam_responses 
        ALTER COLUMN question_embedding TYPE vector USING question_embedding::vector,
        ALTER COLUMN response_embedding TYPE vector USING response_embedding::vector;
    """)

def downgrade() -> None:
    # Revert to 384 dimensions if needed
    op.execute("""
        ALTER TABLE exam_responses 
        ALTER COLUMN question_embedding TYPE vector(384) USING question_embedding::vector(384),
        ALTER COLUMN response_embedding TYPE vector(384) USING response_embedding::vector(384);
    """)