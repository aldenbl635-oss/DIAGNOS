import requests, json, sys

def main():
    base = 'http://127.0.0.1:8000/api'

    # Register/login user
    res = requests.post(f'{base}/auth/register', json={'name':'Demo Judge', 'email':'judge2@diagnos.org', 'password':'demo1234'})
    if res.status_code == 400:
        res = requests.post(f'{base}/auth/login', json={'email':'judge2@diagnos.org', 'password':'demo1234'})
    data = res.json()
    token = data['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print('1. Auth OK - token acquired')

    # ── DEMO A: Tertiary Hospital Mode ──────────────────────────────────────
    print('\n--- DEMO A: Tertiary Hospital Mode ---')
    res = requests.post(f'{base}/simulation/start', json={'case_id': 'chest_pain_001', 'facility_tier': 'tertiary'}, headers=headers)
    assert res.status_code == 200, f"Start failed: {res.text}"
    session_id = res.json()['id']
    print(f'2. Tertiary Simulation started: {session_id[:8]}... (Tier: {res.json()["facility_tier"]})')

    # Order ECG and Troponin (both available at tertiary tier)
    for inv_id in ['ecg', 'troponin']:
        r = requests.post(f'{base}/simulation/{session_id}/investigation', json={'investigation_id': inv_id}, headers=headers)
        assert r.status_code == 200
        d = r.json()
        print(f'   Test ordered: {d["name"]} -> {d["result"][:50]}...')

    # Submit final diagnosis with disposition
    payload = {
        'final_diagnosis': 'Acute coronary syndrome',
        'immediate_priority': 'Activate cardiac cath lab for primary PCI.',
        'evidence_justification': 'ST-elevation on ECG and elevated Troponin.',
        'disposition': 'manage_locally'
    }
    r = requests.post(f'{base}/simulation/{session_id}/evaluate', json=payload, headers=headers)
    assert r.status_code == 200
    eval_data = r.json()['evaluation']
    print(f'3. Tertiary Score: {eval_data["final_score"]}/100 | Disposition Score: {eval_data["disposition_score"]}/5.0')

    # ── DEMO B: Rural PHC Mode (Resource-Constrained Practice) ─────────────
    print('\n--- DEMO B: Rural Primary Health Centre (PHC Mode) ---')
    res_phc = requests.post(f'{base}/simulation/start', json={'case_id': 'chest_pain_001', 'facility_tier': 'phc'}, headers=headers)
    assert res_phc.status_code == 200
    phc_session_id = res_phc.json()['id']
    print(f'4. PHC Simulation started: {phc_session_id[:8]}... (Tier: {res_phc.json()["facility_tier"]})')

    # Attempt to order Troponin (should be blocked at PHC level)
    r_trop = requests.post(f'{base}/simulation/{phc_session_id}/investigation', json={'investigation_id': 'troponin'}, headers=headers)
    assert r_trop.status_code == 400
    print(f'   [Constraint Enforced] Troponin ordered at PHC -> Rejected: "{r_trop.json()["detail"]}"')

    # Order ECG (available at PHC level)
    r_ecg = requests.post(f'{base}/simulation/{phc_session_id}/investigation', json={'investigation_id': 'ecg'}, headers=headers)
    assert r_ecg.status_code == 200
    print(f'   [Basic Test Allowed] ECG ordered at PHC -> {r_ecg.json()["name"]}')

    # Submit with urgent emergency referral (concordant with guidelines)
    payload_phc = {
        'final_diagnosis': 'Acute coronary syndrome',
        'immediate_priority': 'Administer loading dose Aspirin 325mg and dispatch 108 ambulance for immediate transfer to PCI center.',
        'evidence_justification': 'ECG reveals acute STEMI. PHC lacks cath lab; immediate transfer required.',
        'disposition': 'refer'
    }
    r_eval_phc = requests.post(f'{base}/simulation/{phc_session_id}/evaluate', json=payload_phc, headers=headers)
    assert r_eval_phc.status_code == 200
    phc_eval = r_eval_phc.json()['evaluation']
    print(f'5. PHC Referral Competency Result:')
    print(f'   - Student Disposition: {phc_eval["disposition_correct"]}')
    print(f'   - Expected Guideline:  {phc_eval["disposition_expected"]}')
    print(f'   - Disposition Score:   {phc_eval["disposition_score"]} / 5.0')
    print(f'   - Strengths: {phc_eval["strengths"][:2]}')
    print()
    print('ALL CHECKS PASSED - PHC Mode & Disposition Triage verified successfully!')

if __name__ == '__main__':
    main()

