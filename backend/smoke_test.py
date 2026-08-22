import requests, json, sys

base = 'http://127.0.0.1:8000/api'

# Register user
res = requests.post(f'{base}/auth/register', json={'name':'Demo Judge', 'email':'judge2@diagnos.org', 'password':'demo1234'})
if res.status_code == 400:
    res = requests.post(f'{base}/auth/login', json={'email':'judge2@diagnos.org', 'password':'demo1234'})
data = res.json()
token = data['access_token']
headers = {'Authorization': f'Bearer {token}'}
print('1. Auth OK - token acquired')

# Start simulation
res = requests.post(f'{base}/simulation/start', json={'case_id': 'chest_pain_001'}, headers=headers)
assert res.status_code == 200, f"Start failed: {res.text}"
session_id = res.json()['id']
print(f'2. Simulation started: {session_id[:8]}...')

# Ask questions
for q in ['Does the pain radiate to your arm?', 'Do you have diabetes?', 'Do you smoke?']:
    r = requests.post(f'{base}/simulation/{session_id}/question', json={'question': q}, headers=headers)
    assert r.status_code == 200
    d = r.json()
    print(f'   Q: "{q[:30]}..." -> category:{d["category"]}')

# Request cardiovascular examination
r = requests.post(f'{base}/simulation/{session_id}/examination', json={'examination_type': 'cardiovascular'}, headers=headers)
assert r.status_code == 200
print(f'3. Exam OK: {r.json()["result"][:60]}...')

# Order ECG and Troponin
for inv_id in ['ecg', 'troponin']:
    r = requests.post(f'{base}/simulation/{session_id}/investigation', json={'investigation_id': inv_id}, headers=headers)
    assert r.status_code == 200
    d = r.json()
    print(f'4. {d["name"]}: cost={d["cost"]}cr, remaining={d["remaining_resources"]}cr')

# Update differentials
diffs = [{'diagnosis': 'Acute coronary syndrome', 'confidence': 85}, {'diagnosis': 'Pulmonary embolism', 'confidence': 10}]
r = requests.post(f'{base}/simulation/{session_id}/diagnosis', json={'differential_diagnoses': diffs}, headers=headers)
assert r.status_code == 200
print(f'5. Differentials updated OK')

# Submit final diagnosis and evaluate
payload = {
    'final_diagnosis': 'Acute coronary syndrome',
    'immediate_priority': 'Activate cath lab for primary PCI. Administer aspirin 325mg, nitroglycerin, and heparin.',
    'evidence_justification': 'ECG shows ST-elevation in leads II, III, aVF. Troponin I significantly elevated at 1.85ng/mL. Patient has T2DM, is active smoker, hypertensive.'
}
r = requests.post(f'{base}/simulation/{session_id}/evaluate', json=payload, headers=headers)
assert r.status_code == 200
result = r.json()
eval_data = result['evaluation']
print(f'6. Final score: {eval_data["final_score"]}/100')
print(f'   History: {eval_data["history_score"]}/20')
print(f'   Investigation: {eval_data["investigation_score"]}/20')
print(f'   Resource efficiency: {eval_data["resource_efficiency_score"]}/5')
print(f'   Strengths: {eval_data["strengths"][:2]}')
print()
print('ALL CHECKS PASSED - DiagnOS simulation workflow verified!')
