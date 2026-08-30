from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import SimulationSession, User
from routes.auth import get_current_user
import traceback

try:
    db = SessionLocal()
    client = TestClient(app, raise_server_exceptions=True)
    
    # Try all in_progress sessions to find the one crashing
    sessions = db.query(SimulationSession).filter(SimulationSession.status == "in_progress").all()
    if not sessions:
        print("No in-progress sessions found.")
    for session in sessions:
        user = db.query(User).filter(User.id == session.user_id).first()
        app.dependency_overrides[get_current_user] = lambda u=user: u

        print(f"\n--- Testing session {session.id} for user {user.id} ---")
        try:
            resp = client.post(
                f"/api/simulation/{session.id}/evaluate",
                json={"final_diagnosis": "Test", "immediate_priority": "Test", "evidence_justification": "Test"}
            )
            print("Status", resp.status_code)
            if resp.status_code != 200:
                print("Response:", resp.text)
        except Exception as e:
            print("CATCH EXCEPTION!")
            traceback.print_exc()
            break
            
except Exception as e:
    traceback.print_exc()
