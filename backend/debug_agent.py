"""Direct test of migraine_001 through PatientAgent (no HTTP)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import traceback
from ai.patient_agent import PatientAgent
from ai.patient_state import PatientAgentState
from database import SessionLocal
from models import Case

db = SessionLocal()
case = db.query(Case).filter(Case.id == "migraine_001").first()
if not case:
    print("ERROR: migraine_001 not in DB")
    sys.exit(1)

case_data = case.data
agent = PatientAgent(case_data)
state = PatientAgentState.initialize_from_case(case_data)

questions = [
    "Can you describe what the headache feels like?",
    "Does bright light make it worse?",
    "Are you feeling nauseated?",
    "What medication do you take for this?",
    "How are you feeling right now?",
]

for q in questions:
    try:
        conv = [{"role": "student", "text": q}]
        updated_state, output = agent.generate_response(state, conv, q)
        state = updated_state
        print(f"Q: {q}")
        print(f"A: {output.get('response', 'NO RESPONSE')}")
        print()
    except Exception as e:
        print(f"ERROR on '{q}': {e}")
        traceback.print_exc()

db.close()
