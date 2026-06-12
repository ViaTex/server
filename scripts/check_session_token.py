import sys
import os

sys.path.append(r"c:\Users\ASUS\OneDrive\Desktop\disha_setu\server")

from app.core.database import SessionLocal
from app.models.user import UserSession, Mentor
from app.core.security import SecurityManager

def main():
    db = SessionLocal()
    try:
        session = db.query(UserSession).filter(UserSession.user_type == "MENTOR").order_by(UserSession.created_at.desc()).first()
        if not session:
            print("No mentor sessions found!")
            return
        
        print("Found mentor session token.")
        try:
            payload = SecurityManager.verify_token(session.session_token)
            print("Decoded token payload:", payload)
            
            # Let's query Mentor by the token sub ID
            sub_id = payload.get("sub")
            print(f"Token sub ID: {sub_id}")
            
            mentor_by_id = db.query(Mentor).filter(Mentor.id == sub_id).first()
            print("Mentor found by ID:", mentor_by_id.name if mentor_by_id else "None")
            
            mentor_by_user_id = db.query(Mentor).filter(Mentor.user_id == sub_id).first()
            print("Mentor found by User ID:", mentor_by_user_id.name if mentor_by_user_id else "None")
        except Exception as e:
            print(f"Token decoding/lookup error: {e}")
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
