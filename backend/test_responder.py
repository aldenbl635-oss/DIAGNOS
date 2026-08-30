import json
from ai.offline_responder import OfflinePatientResponder
from ai.patient_agent import PatientAgentState
from database import SessionLocal
from models import Case
db = SessionLocal()
c = db.query(Case).first()
if not c:
    print("NO CASE")
    exit()

state = PatientAgentState.initialize_from_case(c.data)
responder = OfflinePatientResponder(c.data)
try:
    res = responder.respond("Can you describe what the discomfort feels like?", state, {"intent": "neutral"})
    print("SUCCESS", res)
except Exception as e:
    import traceback
    traceback.print_exc()
