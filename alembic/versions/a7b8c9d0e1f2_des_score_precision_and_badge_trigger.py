"""Adjust DES score precision and enforce badge trigger

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-03-18

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE students
        ALTER COLUMN current_des_score TYPE NUMERIC(4,2)
        USING current_des_score::numeric(4,2)
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION students_set_badge_from_des_score()
        RETURNS trigger AS $$
        BEGIN
            NEW.badge := CASE
                WHEN COALESCE(NEW.current_des_score, 0.0) < 3.0 THEN 'Bronze'
                WHEN COALESCE(NEW.current_des_score, 0.0) < 5.0 THEN 'Silver'
                WHEN COALESCE(NEW.current_des_score, 0.0) < 7.0 THEN 'Gold'
                ELSE 'Diamond'
            END;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_students_set_badge_from_des_score ON students;
        CREATE TRIGGER trg_students_set_badge_from_des_score
        BEFORE INSERT OR UPDATE OF current_des_score ON students
        FOR EACH ROW
        EXECUTE FUNCTION students_set_badge_from_des_score();
        """
    )

    op.execute(
        """
        UPDATE students
        SET badge = CASE
            WHEN COALESCE(current_des_score, 0.0) < 3.0 THEN 'Bronze'
            WHEN COALESCE(current_des_score, 0.0) < 5.0 THEN 'Silver'
            WHEN COALESCE(current_des_score, 0.0) < 7.0 THEN 'Gold'
            ELSE 'Diamond'
        END
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_students_set_badge_from_des_score ON students;
        DROP FUNCTION IF EXISTS students_set_badge_from_des_score();
        """
    )

    op.execute(
        """
        ALTER TABLE students
        ALTER COLUMN current_des_score TYPE NUMERIC(3,2)
        USING LEAST(current_des_score, 9.99)::numeric(3,2)
        """
    )
