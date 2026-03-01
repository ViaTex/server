"""Add student_info table

Revision ID: 002
Revises: 001
Create Date: 2026-03-01 14:00:00.000000

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
    # Create student_info table
    op.create_table(
        'student_info',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  nullable=False, unique=True),
        
        # Profile Status
        sa.Column('is_complete', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_draft', sa.Boolean(), default=True, nullable=False),
        
        # Mandatory Profile Fields
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(20), nullable=True),
        
        # Location (JSONB for flexibility)
        sa.Column('location', postgresql.JSONB(), nullable=True,
                  comment='JSON: {city, state, country, pincode}'),
        
        # Education Array
        sa.Column('education', postgresql.JSONB(), nullable=True, default=[],
                  comment='Array of education entries'),
        
        # Skills Array
        sa.Column('skills', postgresql.JSONB(), nullable=True, default=[],
                  comment='Array of skill entries'),
        
        # Projects Array
        sa.Column('projects', postgresql.JSONB(), nullable=True, default=[],
                  comment='Array of project entries'),
        
        # Bio Fields
        sa.Column('bio', sa.Text(), nullable=True,
                  comment='AI-generated or manually edited bio'),
        sa.Column('bio_is_ai_generated', sa.Boolean(), default=False, nullable=False,
                  comment='Whether the bio was AI-generated'),
        sa.Column('bio_is_edited', sa.Boolean(), default=False, nullable=False,
                  comment='Whether the AI bio was edited by user'),
        
        # Profile completion percentage
        sa.Column('completion_percentage', sa.Integer(), default=0, nullable=False,
                  comment='Profile completion percentage (0-100)'),
        
        # Audit timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes
    op.create_index('ix_student_info_id', 'student_info', ['id'])
    op.create_index('ix_student_info_user_id', 'student_info', ['user_id'], unique=True)
    op.create_index('ix_student_info_is_complete', 'student_info', ['is_complete'])
    
    # Create GIN index for JSONB fields to enable efficient querying
    op.execute('''
        CREATE INDEX ix_student_info_skills_gin ON student_info USING GIN (skills);
    ''')
    op.execute('''
        CREATE INDEX ix_student_info_education_gin ON student_info USING GIN (education);
    ''')


def downgrade() -> None:
    # Drop GIN indexes
    op.execute('DROP INDEX IF EXISTS ix_student_info_skills_gin;')
    op.execute('DROP INDEX IF EXISTS ix_student_info_education_gin;')
    
    # Drop regular indexes
    op.drop_index('ix_student_info_is_complete', table_name='student_info')
    op.drop_index('ix_student_info_user_id', table_name='student_info')
    op.drop_index('ix_student_info_id', table_name='student_info')
    
    # Drop table
    op.drop_table('student_info')
