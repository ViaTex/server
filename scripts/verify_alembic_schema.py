"""
Compare PostgreSQL tables to SQLAlchemy models. Run from server root with venv:

    cd ~/server && source venv/bin/activate && python scripts/verify_alembic_schema.py

Exit code 0 = columns on checked tables match models. Non-zero = mismatch.

---------------------------------------------------------------------------
If this reports MISSING columns but `alembic current` shows (head):

  You likely used `alembic stamp head` (or stamped a revision) without
  running the actual migrations. Alembic then thinks the DB is up to date,
  so `alembic upgrade head` applies nothing.

  Fix (after a DB backup):

  1. Discover the last revision whose schema you ACTUALLY have. Compare
     columns in psql (\\d students) with what each migration in
     alembic/versions/ adds/changes, working backward from head.

  2. Point Alembic at that revision only (updates alembic_version row):

       alembic stamp <revision_id>

     Example — if your live schema matches the DB *after* migration
     9f2a1b3c4d5e and *before* 7c3a2d9f1b2e (education JSON):

       alembic stamp 9f2a1b3c4d5e

  3. Apply real migrations:

       alembic upgrade head

  NEVER use `alembic stamp head` to "fix" migration errors unless the
  database was restored from a backup that already ran `upgrade head`
  successfully.

  Safe deploy sequence: pull code -> pip install -> `alembic upgrade head`
  -> restart app. Do not stamp head as a shortcut.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import sys
from pathlib import Path

# server/ is the package root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, inspect  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models.user import Student  # noqa: E402


def _model_column_names(table) -> set[str]:
    return {c.name for c in table.columns}


def check_table(engine, tablename: str, model_table) -> tuple[set[str], set[str]]:
    insp = inspect(engine)
    if not insp.has_table(tablename):
        return set(_model_column_names(model_table)), set()
    db_cols = {c["name"] for c in insp.get_columns(tablename)}
    model_cols = _model_column_names(model_table)
    missing = model_cols - db_cols
    return missing, db_cols


def main() -> int:
    engine = create_engine(settings.DATABASE_URL)
    missing, db_cols = check_table(engine, "students", Student.__table__)
    if not db_cols:
        print("ERROR: table 'students' does not exist.")
        return 2
    if missing:
        print("SCHEMA MISMATCH: model expects columns missing from database:")
        for name in sorted(missing):
            print(f"  - students.{name}")
        print()
        print(f"alembic thinks: run `alembic current` (may incorrectly show head).")
        print(f"DATABASE_URL host/db: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else '(hidden)'}")
        return 1
    print("OK: students table has all columns required by the Student model.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
