"""Refactor education to JSON

Revision ID: 7c3a2d9f1b2e
Revises: 9f2a1b3c4d5e
Create Date: 2026-03-17

"""
from typing import Sequence, Union
import json
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7c3a2d9f1b2e"
down_revision: Union[str, None] = "9f2a1b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _infer_level(degree: str | None) -> str:
    if not degree:
        return "Other"
    s = degree.lower()
    if "diploma" in s:
        return "Diploma"
    if "b.tech" in s or "btech" in s or "bachelor" in s:
        return "UG"
    if "m.tech" in s or "mtech" in s or "master" in s:
        return "PG"
    if "12" in s or "xii" in s:
        return "12th"
    if "10" in s or "x" in s:
        return "10th"
    return "Other"


def _year_to_date_str(value: object) -> str:
    try:
        year = int(value)
    except Exception:
        return ""
    if year <= 0:
        return ""
    return f"{year:04d}-01-01"


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column(
            "education",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT id,
                   institution,
                   degree,
                   branch,
                   major,
                   graduation_year,
                   tenth_grade_percentage,
                   twelfth_grade_percentage,
                   btech_cgpa
            FROM students
            """
        )
    ).mappings().all()

    for row in rows:
        entries: list[dict] = []

        if any(
            [
                row.get("institution"),
                row.get("degree"),
                row.get("branch"),
                row.get("major"),
                row.get("graduation_year"),
                row.get("btech_cgpa"),
            ]
        ):
            level = _infer_level(row.get("degree"))
            degree = (row.get("degree") or "").strip()
            custom_level = degree if level == "Other" and degree else "Not specified" if level == "Other" else ""

            description_parts = []
            if row.get("branch"):
                description_parts.append(f"Branch: {row['branch']}")
            if row.get("major"):
                description_parts.append(f"Major: {row['major']}")

            entries.append(
                {
                    "id": str(uuid.uuid4()),
                    "level": level,
                    "custom_level": custom_level,
                    "institution": (row.get("institution") or "").strip() or "Unknown",
                    "start_date": "",
                    "end_date": _year_to_date_str(row.get("graduation_year")),
                    "score": str(row.get("btech_cgpa")).strip() if row.get("btech_cgpa") is not None else "",
                    "description": "; ".join(description_parts),
                }
            )

        if row.get("tenth_grade_percentage") is not None:
            entries.append(
                {
                    "id": str(uuid.uuid4()),
                    "level": "10th",
                    "custom_level": "",
                    "institution": "Unknown",
                    "start_date": "",
                    "end_date": "",
                    "score": str(row.get("tenth_grade_percentage")),
                    "description": "",
                }
            )

        if row.get("twelfth_grade_percentage") is not None:
            entries.append(
                {
                    "id": str(uuid.uuid4()),
                    "level": "12th",
                    "custom_level": "",
                    "institution": "Unknown",
                    "start_date": "",
                    "end_date": "",
                    "score": str(row.get("twelfth_grade_percentage")),
                    "description": "",
                }
            )

        if entries:
            conn.execute(
                sa.text("UPDATE students SET education = :education WHERE id = :id"),
                {"education": json.dumps(entries), "id": row["id"]},
            )

    op.drop_column("students", "tenth_grade_percentage")
    op.drop_column("students", "twelfth_grade_percentage")
    op.drop_column("students", "btech_cgpa")
    op.drop_column("students", "institution")
    op.drop_column("students", "degree")
    op.drop_column("students", "branch")
    op.drop_column("students", "graduation_year")
    op.drop_column("students", "major")


def downgrade() -> None:
    op.add_column("students", sa.Column("major", sa.String(length=100), nullable=True))
    op.add_column("students", sa.Column("graduation_year", sa.Integer(), nullable=True))
    op.add_column("students", sa.Column("branch", sa.String(length=100), nullable=True))
    op.add_column("students", sa.Column("degree", sa.String(length=100), nullable=True))
    op.add_column("students", sa.Column("institution", sa.String(length=255), nullable=True))
    op.add_column("students", sa.Column("btech_cgpa", sa.Float(), nullable=True))
    op.add_column("students", sa.Column("twelfth_grade_percentage", sa.Float(), nullable=True))
    op.add_column("students", sa.Column("tenth_grade_percentage", sa.Float(), nullable=True))

    op.drop_column("students", "education")
