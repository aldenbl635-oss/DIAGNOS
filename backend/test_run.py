import sys, json, traceback
sys.path.append('.')

from ai.offline_responder import OfflinePatientResponder
from ai.patient_state import PatientAgentState

state = PatientAgentState()

with open('case_engine/cases/chest_pain_002.json', 'r') as f:
    case_data = json.load(f)

responder = OfflinePatientResponder(case_data)
try:
    res = responder.respond(
        "calm down",
        state,
        {'intent': 'Reassurance', 'tone': 'Neutral'}
    )
    print('SUCCESS:')
    print(json.dumps(res, indent=2))
except Exception as e:
    print('EXCEPTION:')
    traceback.print_exc()
