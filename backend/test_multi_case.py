"""
Multi-case smoke test: Migraine, Stroke, and a Chest-Pain (GERD) case.
Tests the core questions and cross-case isolation.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
from ai.patient_agent import PatientAgent
from ai.patient_state import PatientAgentState
from database import SessionLocal
from models import Case

db = SessionLocal()

CASES_TO_TEST = [
    {
        "id": "migraine_001",
        "questions": [
            ("Can you describe what the headache feels like?", ["head", "right", "eye", "temple", "throbbing", "severe"], []),
            ("Does bright light make it worse?", ["light", "yes", "bother", "sensitive"], []),
            ("Are you feeling nauseated?", ["nausea", "sick", "stomach", "queasy"], []),
            ("What medication do you take for this?", ["sumatriptan"], ["amlodipine", "aspirin"]),
            ("Have you had this type of headache before?", ["before", "similar", "migraine", "had", "history"], []),
        ],
    },
    {
        "id": "stroke_001",
        "questions": [
            ("What is your main problem?", ["arm", "leg", "weak", "speech", "droop", "mouth", "slur", "numb", "stroke", "heavy"], []),
            ("Can you tell me where you feel the weakness?", ["left", "arm", "leg", "side"], []),
            ("Are you experiencing any chest pain?", [], ["crushing", "cardiac", "myocardial"]),
        ],
    },
    {
        "id": "chest_pain_003",  # GERD case
        "questions": [
            ("Can you describe what the pain feels like?", ["burn", "chest", "stomach", "discomfort", "heartburn"], []),
            ("What makes it worse?", ["lie", "bend", "recumb", "flat", "eating", "food", "worse", "positional"], []),
        ],
    },
]

SEPARATOR = "=" * 60

failures = []

for case_info in CASES_TO_TEST:
    cid = case_info["id"]
    case = db.query(Case).filter(Case.id == cid).first()
    if not case:
        print(f"\nSKIPPED: {cid} not in DB")
        continue
    print(f"\n{SEPARATOR}")
    print(f"CASE: {cid}")
    print(SEPARATOR)

    case_data = case.data
    agent = PatientAgent(case_data)
    state = PatientAgentState.initialize_from_case(case_data)
    conv = []

    for q, expect, exclude in case_info["questions"]:
        conv.append({"role": "student", "text": q})
        try:
            updated_state, output = agent.generate_response(state, conv, q)
            state = updated_state
        except Exception as e:
            print(f"ERROR: {e}")
            failures.append({"case": cid, "q": q, "error": str(e)})
            continue

        answer = output.get("response", "")
        conv.append({"role": "patient", "text": answer})
        al = answer.lower()

        print(f"\nQ: {q}")
        print(f"A: {answer}")

        # Expect check
        if expect:
            found = any(kw in al for kw in expect)
            if not found:
                print(f"  FAIL: expected one of {expect}")
                failures.append({"case": cid, "q": q, "reason": f"expected {expect}", "answer": answer})
            else:
                mf = next(kw for kw in expect if kw in al)
                print(f"  PASS: found '{mf}'")

        # Exclude check
        for bad in exclude:
            if bad in al:
                print(f"  FAIL: found forbidden '{bad}'")
                failures.append({"case": cid, "q": q, "reason": f"contains forbidden '{bad}'", "answer": answer})
            else:
                print(f"  PASS: no '{bad}'")

print(f"\n{SEPARATOR}")
if failures:
    print(f"RESULT: {len(failures)} FAILURE(S)")
    for f in failures:
        print(f"  [{f.get('case')}] Q: {f.get('q')}")
        print(f"    REASON: {f.get('reason', f.get('error', ''))}")
        print(f"    ANSWER: {f.get('answer', '')[:150]}")
else:
    print("RESULT: ALL TESTS PASSED")
print(SEPARATOR)

db.close()
