import sys
import os
# pyrefly: ignore [missing-import]
from sqlalchemy import text

# Add the server directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine

def main():
    print("Connecting to the database to add mentor profile social link columns...")
    
    statements = [
        "ALTER TABLE mentors ADD COLUMN IF NOT EXISTS linkedin_profile VARCHAR(500);",
        "ALTER TABLE mentors ADD COLUMN IF NOT EXISTS github_profile VARCHAR(500);",
        "ALTER TABLE mentors ADD COLUMN IF NOT EXISTS personal_website VARCHAR(500);"
    ]
    
    with engine.begin() as conn:
        for stmt in statements:
            print(f"Executing: {stmt}")
            conn.execute(text(stmt))
            
    print("Database columns successfully added/verified!")

if __name__ == "__main__":
    main()
