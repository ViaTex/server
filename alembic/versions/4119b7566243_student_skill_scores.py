"""student skill scores

Revision ID: 4119b7566243
Revises: 724dfc75d8ac
Create Date: 2026-06-11 22:00:30.427607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4119b7566243'
down_revision: Union[str, None] = '724dfc75d8ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create the student_skill_scores table with precise typologies
    op.create_table(
        'student_skill_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # Foreign Key Constraints mapping to the exact table names
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['exam_sessions.id'], ondelete='CASCADE'),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # 2. Performance Indices
    # Composite index on (student_id, topic_id) for fast historical trend queries
    op.create_index(
        'ix_student_skill_scores_student_id_topic_id',
        'student_skill_scores',
        ['student_id', 'topic_id']
    )
    
    # Index on created_at for fast chronological sorting
    op.create_index(
        'ix_student_skill_scores_created_at',
        'student_skill_scores',
        ['created_at']
    )
def downgrade() -> None:
    # Remove indices first
    op.drop_index('ix_student_skill_scores_created_at', table_name='student_skill_scores')
    op.drop_index('ix_student_skill_scores_student_id_topic_id', table_name='student_skill_scores')
    
    # Drop the table
    op.drop_table('student_skill_scores')