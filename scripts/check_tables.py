import sys
import os

sys.path.append(r"c:\Users\ASUS\OneDrive\Desktop\disha_setu\server")

from app.core.database import SessionLocal, Base
from sqlalchemy import inspect

def main():
    db = SessionLocal()
    try:
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        print("Tables in database:", tables)
        
        # Let's query one UserSession row if it exists
        if "user_sessions" in tables:
            from sqlalchemy import text
            row = db.execute(text("select * from user_sessions limit 1")).fetchone()
            print("User session sample:", row)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
