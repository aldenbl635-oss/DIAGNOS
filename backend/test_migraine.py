"""
test_migraine.py - Migraine_001 end-to-end test suite.

Tests the 10 required questions, cross-case isolation, and performance.

Usage (from backend root):
    venv/Scripts/python test_migraine.py
"""
import time
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import User, Case
from routes.auth import get_current_user

# Pre-warm the embedding model
from ai.embedding_service import EmbeddingService
print("[Setup] Loading embedding model...")
EmbeddingService()
print("[Setup] Done.\n")

db = SessionLocal()
user = db.query(User).first()
if not user:
    print("ERROR: No user found in database. Please seed the DB first.")
    sys.exit(1)

app.dependency_overrides[get_current_user] = lambda: user
client = TestClient(app)


# ---- Helpers ---------------------------------------------------------------

def start_session(case_id: str) -> str:
    resp = client.post("/api/simulation/start", json={"case_id": case_id})
    assert resp.status_code == 200, f"Start failed {resp.status_code}: {resp.text}"
    return resp.json()["id"]


def ask(session_id: str, question: str):
    t0 = time.time()
    resp = client.post(f"/api/simulation/{session_id}/question", json={"question": question})
    ms = (time.time() - t0) * 1000
    assert resp.status_code == 200, f"Question failed {resp.status_code}: {resp.text}"
    return resp.json().get("answer", ""), ms


def check_contains(answer: str, keywords: list, label: str):
    al = answer.lower()
    for kw in keywords:
        if kw.lower() in al:
            print(f"  PASS [{label}]: found '{kw}'")
            return True
    print(f"  FAIL [{label}]: NONE OF {keywords} in answer: {answer[:200]}")
    return False


def check_excludes(answer: str, bad_keywords: list, label: str):
    al = answer.lower()
    for kw in bad_keywords:
        if kw.lower() in al:
            print(f"  FAIL [{label}]: found forbidden '{kw}' in: {answer[:200]}")
            return False
    print(f"  PASS [{label}]: none of {bad_keywords} present")
    return True


# ---- Main ------------------------------------------------------------------

def run():
    failures = []
    latencies = []

    migraine_case = db.query(Case).filter(Case.id == "migraine_001").first()
    if not migraine_case:
        print("ERROR: migraine_001 not found in DB. Run setup_migraine.py first.")
        sys.exit(1)

    print("=" * 65)
    print("MIGRAINE_001 -- 10-Question Test Suite")
    print("=" * 65)

    session_id = start_session("migraine_001")
    print(f"Session: {session_id}\n")

    def run_q(question, expect=None, exclude=None, label=""):
        answer, ms = ask(session_id, question)
        latencies.append(ms)
        print(f"\nQ: {question}")
        print(f"A: {answer}")
        print(f"   [{ms:.0f} ms]")
        ok = True
        if expect:
            r = check_contains(answer, expect, label or question[:50])
            if not r:
                failures.append({"label": label or question, "answer": answer,
                                  "reason": f"expected any of {expect}"})
                ok = False
        if exclude:
            r = check_excludes(answer, exclude, label or question[:50])
            if not r:
                failures.append({"label": label or question, "answer": answer,
                                  "reason": f"must not contain {exclude}"})
                ok = False
        return ok

    # 1. Headache description
    run_q(
        "Can you describe what the headache feels like?",
        expect=["headache", "right", "eye", "temple", "throbbing", "severe", "head", "pain"],
        exclude=["chest", "cardiac", "jaw", "crushing"],
        label="Q1_describe_headache",
    )

    # 2. Photophobia
    run_q(
        "Does bright light make it worse?",
        expect=["light", "photophobia", "sensitive", "bother", "bright", "yes"],
        exclude=["chest", "cardiac", "jaw"],
        label="Q2_photophobia",
    )

    # 3. Nausea
    run_q(
        "Are you feeling nauseated?",
        expect=["nausea", "sick", "stomach", "vomiting", "queasy", "yes"],
        exclude=["chest", "cardiac"],
        label="Q3_nausea",
    )

    # 4. Previous episodes
    run_q(
        "Have you experienced this type of headache before?",
        expect=["before", "similar", "migraine", "history", "have", "had", "previous", "yes"],
        exclude=["chest"],
        label="Q4_past_history",
    )

    # 5. Medications
    run_q(
        "What medication do you take for this?",
        expect=["sumatriptan", "medication", "take", "pill", "medicine"],
        exclude=["amlodipine", "atorvastatin", "aspirin", "chest"],
        label="Q5_medications",
    )

    # 6. Pain location
    run_q(
        "Where exactly is the pain located?",
        expect=["right", "eye", "temple", "head", "side", "behind"],
        exclude=["chest"],
        label="Q6_location",
    )

    # 7. Unknown question -- safe fallback (must NOT hallucinate case facts)
    run_q(
        "What did you eat for breakfast?",
        exclude=["sumatriptan", "photophobia", "right-sided", "migraine_001"],
        label="Q7_unknown",
    )

    # 8. No diabetes invented
    run_q(
        "Do you have diabetes or high blood pressure?",
        exclude=["yes, i have diabetes", "i am diabetic"],
        label="Q8_no_invented_diabetes",
    )

    # 9. Radiation to jaw must NOT pull cardiac facts
    run_q(
        "Does the pain spread to your jaw or arm?",
        exclude=["crushing chest pain", "cardiac", "infarction"],
        label="Q9_no_cardiac_radiation",
    )

    # 10. Emotional wellbeing
    run_q(
        "How are you feeling right now?",
        expect=["headache", "worried", "scared", "uncomfortable", "not great",
                "pain", "terrible", "light", "feel"],
        label="Q10_emotional",
    )

    # ---- Cross-case isolation -----------------------------------------------
    print("\n" + "=" * 65)
    print("CROSS-CASE ISOLATION -- Cardiac question in migraine session")
    print("=" * 65)
    answer, ms = ask(session_id, "What does the chest pain feel like?")
    latencies.append(ms)
    print(f"\nQ: What does the chest pain feel like?\nA: {answer}\n   [{ms:.0f} ms]")
    r = check_excludes(
        answer,
        ["crushing", "heavy weight on the chest", "pressure-like chest"],
        "cross_case_isolation",
    )
    if not r:
        failures.append({"label": "cross_case_isolation", "answer": answer,
                          "reason": "cardiac facts leaked into migraine session"})

    # ---- Persistency test ---------------------------------------------------
    print("\n" + "=" * 65)
    print("PERSISTENCY CHECK -- Second migraine session retrieves same facts")
    print("=" * 65)
    session2 = start_session("migraine_001")
    print(f"Session 2: {session2}")
    ans2, ms2 = ask(session2, "What medications do you take?")
    latencies.append(ms2)
    print(f"\nQ: What medications do you take?\nA: {ans2}\n   [{ms2:.0f} ms]")
    r = check_contains(ans2, ["sumatriptan", "medication", "take"], "persistency_medications")
    if not r:
        failures.append({"label": "persistency_medications", "answer": ans2,
                          "reason": "expected sumatriptan in second session"})

    # ---- Summary ------------------------------------------------------------
    avg = sum(latencies) / len(latencies)
    mx  = max(latencies)
    print("\n" + "=" * 65)
    print("PERFORMANCE")
    print(f"  Questions run:   {len(latencies)}")
    print(f"  Avg latency:     {avg:.0f} ms")
    print(f"  Max latency:     {mx:.0f} ms")
    print(f"  First req:       {latencies[0]:.0f} ms")
    print(f"  Second req:      {latencies[1]:.0f} ms")
    print("=" * 65)

    if failures:
        print(f"\nRESULT: {len(failures)} TEST(S) FAILED\n")
        for f in failures:
            print(f"  FAILED TEST:  {f['label']}")
            print(f"  REASON:       {f['reason']}")
            print(f"  ACTUAL:       {f['answer'][:200]}\n")
        sys.exit(1)
    else:
        print("\nRESULT: ALL TESTS PASSED")

    db.close()


if __name__ == "__main__":
    run()
