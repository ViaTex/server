"""Add mentor and skill evaluations

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-04-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


skill_evaluation_status_enum = sa.Enum(
    "submitted",
    "assigned",
    "under_review",
    "viva_scheduled",
    "viva_completed",
    "evaluated",
    name="skillevaluationstatus",
)
skill_evaluation_verdict_enum = sa.Enum(
    "excellent",
    "very_good",
    "good",
    "needs_improvement",
    "did_not_pass",
    name="skillevaluationverdict",
)
skill_evaluation_status_enum_existing = postgresql.ENUM(
    "submitted",
    "assigned",
    "under_review",
    "viva_scheduled",
    "viva_completed",
    "evaluated",
    name="skillevaluationstatus",
    create_type=False,
)
skill_evaluation_verdict_enum_existing = postgresql.ENUM(
    "excellent",
    "very_good",
    "good",
    "needs_improvement",
    "did_not_pass",
    name="skillevaluationverdict",
    create_type=False,
)
user_status_enum_existing = postgresql.ENUM(
    "ACTIVE",
    "INACTIVE",
    "SUSPENDED",
    "PENDING",
    name="userstatus",
    create_type=False,
)


def _add_enum_value_if_missing(bind, enum_name: str, enum_value: str) -> None:
    bind.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_enum
                        WHERE enumlabel = '{enum_value}'
                        AND enumtypid = '{enum_name}'::regtype
                    ) THEN
                        ALTER TYPE {enum_name} ADD VALUE '{enum_value}';
                    END IF;
                END IF;
            END$$;
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    _add_enum_value_if_missing(bind, "usertype", "MENTOR")
    _add_enum_value_if_missing(bind, "sessionusertype", "MENTOR")

    skill_evaluation_status_enum.create(bind, checkfirst=True)
    skill_evaluation_verdict_enum.create(bind, checkfirst=True)

    if not inspector.has_table("mentors"):
        op.create_table(
            "mentors",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=20), nullable=True),
            sa.Column("status", user_status_enum_existing, nullable=True),
            sa.Column("email_verified", sa.Boolean(), nullable=True),
            sa.Column("phone_verified", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("current_role", sa.String(length=255), nullable=True),
            sa.Column("expertise_areas", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("experience_years", sa.Integer(), nullable=True),
            sa.Column("motivation", sa.Text(), nullable=True),
            sa.Column("average_rating", sa.Numeric(precision=3, scale=2), nullable=False, server_default="0.0"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index(op.f("ix_mentors_email"), "mentors", ["email"], unique=True)
        op.create_index(op.f("ix_mentors_user_id"), "mentors", ["user_id"], unique=True)

    if not inspector.has_table("skill_evaluations"):
        op.create_table(
            "skill_evaluations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mentor_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("status", skill_evaluation_status_enum_existing, nullable=False),
            sa.Column("proposed_slots", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("confirmed_slot", sa.DateTime(timezone=True), nullable=True),
            sa.Column("viva_meeting_link", sa.String(length=1000), nullable=True),
            sa.Column("score_technical", sa.Integer(), nullable=True),
            sa.Column("score_practical", sa.Integer(), nullable=True),
            sa.Column("score_communication", sa.Integer(), nullable=True),
            sa.Column("score_originality", sa.Integer(), nullable=True),
            sa.Column("total_score", sa.Integer(), nullable=True),
            sa.Column("verdict", skill_evaluation_verdict_enum_existing, nullable=True),
            sa.Column("feedback_strengths", sa.Text(), nullable=True),
            sa.Column("feedback_improvements", sa.Text(), nullable=True),
            sa.Column("student_rating_of_mentor", sa.Integer(), nullable=True),
            sa.Column("student_technical_issues", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["mentor_id"], ["mentors.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_skill_evaluations_mentor_id"), "skill_evaluations", ["mentor_id"], unique=False)
        op.create_index(op.f("ix_skill_evaluations_student_id"), "skill_evaluations", ["student_id"], unique=False)
        op.create_index(op.f("ix_skill_evaluations_project_id"), "skill_evaluations", ["project_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("skill_evaluations"):
        op.drop_index(op.f("ix_skill_evaluations_project_id"), table_name="skill_evaluations")
        op.drop_index(op.f("ix_skill_evaluations_student_id"), table_name="skill_evaluations")
        op.drop_index(op.f("ix_skill_evaluations_mentor_id"), table_name="skill_evaluations")
        op.drop_table("skill_evaluations")

    if inspector.has_table("mentors"):
        op.drop_index(op.f("ix_mentors_user_id"), table_name="mentors")
        op.drop_index(op.f("ix_mentors_email"), table_name="mentors")
        op.drop_table("mentors")

    skill_evaluation_verdict_enum.drop(bind, checkfirst=True)
    skill_evaluation_status_enum.drop(bind, checkfirst=True)
