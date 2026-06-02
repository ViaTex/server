"""
Dev utility: manually mark a user's email as verified.

Usage:
    python scripts/verify_user.py <email>
    python scripts/verify_user.py hr@gmail.com
    python scripts/verify_user.py --all          # verify ALL unverified users
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.models.user import Student, Mentor, Corporate, College, Admin

MODELS = [
    (Student, "student"),
    (Mentor, "mentor"),
    (Corporate, "corporate"),
    (College, "college"),
    (Admin, "admin"),
]


def verify_user(email: str, db) -> bool:
    email = email.strip().lower()
    for Model, user_type in MODELS:
        user = db.query(Model).filter(Model.email == email).first()
        if user:
            if user.email_verified:
                print(f"[{user_type}] {email} — already verified ✓")
            else:
                user.email_verified = True
                db.commit()
                print(f"[{user_type}] {email} — email_verified set to True ✅")
            return True
    print(f"✗ No user found with email: {email}")
    return False


def verify_all(db):
    total = 0
    for Model, user_type in MODELS:
        users = db.query(Model).filter(Model.email_verified == False).all()
        for user in users:
            user.email_verified = True
            print(f"[{user_type}] {user.email} — verified ✅")
            total += 1
    db.commit()
    print(f"\nDone. {total} user(s) verified.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    db = next(get_db())

    if sys.argv[1] == "--all":
        verify_all(db)
    else:
        for email in sys.argv[1:]:
            verify_user(email, db)


if __name__ == "__main__":
    main()
