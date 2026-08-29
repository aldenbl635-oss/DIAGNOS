import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import json

from database import Base, get_db
from main import app
from config import settings
import models
from case_engine.engine import case_engine

# Use a test database file
TEST_DATABASE_URL = "sqlite:///./test_diagnos.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    
    # Pre-seed cases in test DB
    db = TestingSessionLocal()
    for case_id, case_data in case_engine.cases.items():
        db_case = db.query(models.Case).filter(models.Case.id == case_id).first()
        if not db_case:
            new_case = models.Case(
                id=case_id,
                title=case_data.get("title"),
                specialty=case_data.get("specialty"),
                difficulty=case_data.get("difficulty"),
                data=case_data
            )
            db.add(new_case)
    db.commit()
    db.close()
    
    yield
    
    # Tear down — dispose engine connections first to release Windows file lock
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import time; time.sleep(0.2)
    try:
        if os.path.exists("./test_diagnos.db"):
            os.remove("./test_diagnos.db")
    except PermissionError:
        pass  # Skip file cleanup on Windows if still locked

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_case_engine_loaded():
    # Verify cases are loaded by engine
    assert "chest_pain_001" in case_engine.cases
    assert case_engine.cases["chest_pain_001"]["title"] == "Chest Discomfort — Emergency Presentation"

def test_register_login(client):
    email = "test_student@diagnos.org"
    password = "password123"
    name = "Test Student"

    # Register
    res = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == email

    # Login
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data

def test_simulation_workflow(client):
    # Register and login to get token
    email = "sim_student@diagnos.org"
    res = client.post("/api/auth/register", json={"name": "Sim Student", "email": email, "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Start simulation
    res = client.post("/api/simulation/start", json={"case_id": "chest_pain_001"}, headers=headers)
    assert res.status_code == 200
    session_data = res.json()
    session_id = session_data["id"]
    assert session_data["remaining_resources"] == 1000

    # Ask question
    res = client.post(f"/api/simulation/{session_id}/question", json={"question": "Does it radiate to your arm?"}, headers=headers)
    assert res.status_code == 200
    q_data = res.json()
    assert "answer" in q_data
    assert q_data["category"] == "pain_characteristics"

    # Ask non-relevant question
    res = client.post(f"/api/simulation/{session_id}/question", json={"question": "What is the color of the sky?"}, headers=headers)
    assert res.status_code == 200
    q_data = res.json()
    assert "answer" in q_data

    # Order ECG investigation
    res = client.post(f"/api/simulation/{session_id}/investigation", json={"investigation_id": "ecg"}, headers=headers)
    assert res.status_code == 200
    inv_data = res.json()
    assert inv_data["cost"] == 100
    assert inv_data["remaining_resources"] == 900

    # Update differential diagnoses
    differentials = [{"diagnosis": "Acute coronary syndrome", "confidence": 75}]
    res = client.post(f"/api/simulation/{session_id}/diagnosis", json={"differential_diagnoses": differentials}, headers=headers)
    assert res.status_code == 200

    # Submit and Evaluate
    submit_payload = {
        "final_diagnosis": "Acute coronary syndrome",
        "immediate_priority": "Aspirin 325mg and cardiac catheterization lab activation.",
        "evidence_justification": "Elevated troponin I, ST-segment elevation on leads II, III, aVF. Risk factors are diabetes and smoking history."
    }
    res = client.post(f"/api/simulation/{session_id}/evaluate", json=submit_payload, headers=headers)
    assert res.status_code == 200
    eval_data = res.json()
    assert "evaluation" in eval_data
    assert eval_data["evaluation"]["final_score"] > 0
    assert "differential_score" in eval_data["evaluation"]

def test_get_session_restore(client):
    email = "restore_student@diagnos.org"
    res = client.post("/api/auth/register", json={"name": "Restore Student", "email": email, "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/simulation/start", json={"case_id": "chest_pain_001"}, headers=headers)
    session_id = res.json()["id"]

    client.post(f"/api/simulation/{session_id}/question", json={"question": "Do you smoke?"}, headers=headers)
    client.post(f"/api/simulation/{session_id}/investigation", json={"investigation_id": "ecg"}, headers=headers)

    res = client.get(f"/api/simulation/{session_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["session"]["case_id"] == "chest_pain_001"
    assert data["session"]["remaining_resources"] == 900
    assert len(data["chat_messages"]) >= 3
    assert "ecg" in data["investigations_ordered"]
    assert data["case"]["patient_name"] == "Daniel Thomas"
    assert len(data["case"]["investigations"]) > 0

def test_case_detail_includes_metadata(client):
    email = "case_detail@diagnos.org"
    res = client.post("/api/auth/register", json={"name": "Case Detail", "email": email, "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/cases/chest_pain_001", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["patient_name"] == "Daniel Thomas"
    assert len(data["examinations"]) >= 5
    assert len(data["investigations"]) >= 5
    assert "vitals" in data


def test_communication_analyzer():
    from ai.communication_analyzer import CommunicationAnalyzer
    analyzer = CommunicationAnalyzer()
    
    # Test alarmist statement
    res = analyzer.analyze("I think you are going to die right now!")
    assert res["intent"] == "alarmist"
    assert res["alarmist"] is True
    assert res["severity"] >= 80

    # Test empathy/supportive statement
    res2 = analyzer.analyze("Take your time, I am right here beside you.")
    assert res2["intent"] == "empathy"
    assert res2["empathetic"] is True

    # Test apology
    res3 = analyzer.analyze("I apologize, I didn't mean to say it like that.")
    assert res3["intent"] == "apology"
    assert res3["apology"] is True


def test_emotional_state_transitions():
    from ai.patient_emotion import EmotionalState
    from ai.patient_personality import PersonalityProfile
    
    # Baseline
    state = EmotionalState(trust=50, fear=20, frustration=10, cooperation=50)
    pers = PersonalityProfile(emotional_sensitivity=80, distrust_of_medical=60, fear_of_death=90, assertiveness=50, cooperativeness=50)
    
    # Apply an alarmist statement and check scaling
    analysis = {
        "intent": "alarmist",
        "tone": "frightening",
        "severity": 90,
        "alarmist": True,
        "empathetic": False,
        "reassurance": False,
        "dismissive": False,
        "threat": False,
        "insult": False,
        "apology": False
    }
    
    delta = state.calculate_transitions(analysis, personality=pers, turn_count=1)
    
    # Should scale higher due to emotional_sensitivity=80 and fear_of_death=90
    assert delta["fear"] > 0
    assert delta["shock"] > 0
    assert delta["frustration"] > 0
    
    # Apply changes
    state.apply_update(delta)
    assert state.fear > 20
    assert state.frustration > 10


def test_patient_agent_memory_reference_and_dataset():
    from ai.patient_agent import PatientAgent
    from ai.patient_state import PatientAgentState
    from case_engine.engine import case_engine
    
    # Load chest pain case
    case = case_engine.cases["chest_pain_001"]
    agent = PatientAgent(case)
    
    state = PatientAgentState()
    state.personality.fear_of_death = 90
    state.personality.assertiveness = 50
    state.emotion.anxiety = 70
    
    # First, student makes an alarmist remark statement
    res1 = agent.generate_response(
        state,
        conversation_history=[],
        student_message="You are about to die! Your heart is failing!"
    )
    new_state = res1[0]
    
    # Ensure memory event logged
    has_alarm_mem = False
    for ev in new_state.memory.events:
        if "student_asked:" in ev.event and "die" in ev.event.lower():
            has_alarm_mem = True
            break
    assert has_alarm_mem is True
    
    # Now student asks "Are you feeling anxious?"
    res2 = agent.generate_response(
        new_state,
        conversation_history=[{"role": "student", "text": "You are about to die! Your heart is failing!"}, {"role": "patient", "text": res1[1]["response"]}],
        student_message="Are you feeling anxious?"
    )
    
    response_text = res2[1]["response"]
    
    # Since there was an alarming memory, the patient response must reference the panic/frightening news!
    assert "Especially after you told me earlier" in response_text or "told me earlier" in response_text or "you told me" in response_text


def test_non_relevant_questions():
    from ai.patient_agent import PatientAgent
    from ai.patient_state import PatientAgentState
    from case_engine.engine import case_engine
    
    case = case_engine.cases["chest_pain_001"]
    agent = PatientAgent(case)
    
    state = PatientAgentState()
    
    # 1. Ask a non-relevant question like "How many legs does a dog have?"
    res1 = agent.generate_response(
        state,
        conversation_history=[],
        student_message="How many legs does a dog have?"
    )
    
    # Check that it did NOT trigger the pain site response ("radiation" or "legs" related pain)
    response_text = res1[1]["response"]
    assert "radiate" not in response_text.lower()
    assert "arm" not in response_text.lower()
    assert "shoulder" not in response_text.lower()
    assert "jaw" not in response_text.lower()
    
    # Check that it returned a query fallback explanation or standard warning
    assert "chest pain" in response_text.lower() or "look up" in response_text.lower() or "not sure" in response_text.lower() or "focus on" in response_text.lower()

    # 2. Ask a relevant question like "Where is the pain located?"
    res2 = agent.generate_response(
        state,
        conversation_history=[],
        student_message="Where is the pain located?"
    )
    
    response_text2 = res2[1]["response"]
    assert "chest" in response_text2.lower() or "discomfort" in response_text2.lower() or "pain" in response_text2.lower()


def test_dynamic_case_pathway_generation():
    from case_engine.pathway import generate_case_expected_pathway
    from case_engine.engine import case_engine

    # 1. Test case with explicit expected_pathway (chest_pain_001)
    case_001 = case_engine.cases["chest_pain_001"]
    pathway_001 = generate_case_expected_pathway(case_001)
    assert len(pathway_001) >= 5
    assert pathway_001[0]["type"] == "system"
    assert "Daniel Thomas" in pathway_001[0]["label"]
    assert any("ECG" in n["label"] for n in pathway_001)
    assert any("Troponin" in n["label"] for n in pathway_001)
    assert pathway_001[-1]["type"] == "decision"
    assert "coronary" in pathway_001[-1]["label"].lower()

    # 2. Test dynamically synthesized pathway from raw case data without explicit expected_pathway
    stroke_case = {
        "title": "Acute Stroke Presentation",
        "patient": {"name": "Eleanor Vance", "chief_complaint": "Slurred speech and arm weakness"},
        "clinical_facts": {"symptoms": ["Sudden left arm weakness", "Slurred speech"]},
        "examinations": [
            {"type": "neurological", "name": "Neurological Examination", "result": "Left facial droop"}
        ],
        "investigations": [
            {"id": "ct_head", "name": "CT Scan of Head", "cost": 350, "result": "Ischemic stroke"}
        ],
        "evaluation_criteria": {
            "correct_diagnosis": "Acute ischemic stroke",
            "required_investigations": ["ct_head"]
        }
    }
    stroke_pathway = generate_case_expected_pathway(stroke_case)
    assert len(stroke_pathway) == 5
    assert "Eleanor Vance" in stroke_pathway[0]["label"]
    assert stroke_pathway[1]["type"] == "question"
    assert stroke_pathway[2]["type"] == "examination"
    assert "Neurological" in stroke_pathway[2]["label"]
    assert stroke_pathway[3]["type"] == "investigation"
    assert "CT Scan of Head" in stroke_pathway[3]["label"]
    assert stroke_pathway[4]["type"] == "decision"
    assert "Acute ischemic stroke" in stroke_pathway[4]["label"]


def test_results_endpoint_includes_case_specific_pathway(client):
    # Register and run simulation for chest_pain_001
    email = "pathway_test@diagnos.org"
    res = client.post("/api/auth/register", json={"name": "Pathway Student", "email": email, "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/simulation/start", json={"case_id": "chest_pain_001"}, headers=headers)
    session_id = res.json()["id"]

    # Ask question, do exam, order test
    client.post(f"/api/simulation/{session_id}/question", json={"question": "Where is the pain located?"}, headers=headers)
    client.post(f"/api/simulation/{session_id}/examination", json={"examination_type": "cardiovascular"}, headers=headers)
    client.post(f"/api/simulation/{session_id}/investigation", json={"investigation_id": "ecg"}, headers=headers)

    submit_payload = {
        "final_diagnosis": "Acute coronary syndrome",
        "immediate_priority": "Aspirin 325mg and cardiac catheterization lab activation.",
        "evidence_justification": "ST elevation in inferior leads and elevated cardiac enzymes."
    }
    eval_res = client.post(f"/api/simulation/{session_id}/evaluate", json=submit_payload, headers=headers)
    assert eval_res.status_code == 200
    eval_json = eval_res.json()
    assert "expected_pathway" in eval_json
    assert len(eval_json["expected_pathway"]) > 0
    assert any("Daniel Thomas" in node["label"] for node in eval_json["expected_pathway"])

    # Test GET results endpoint
    results_res = client.get(f"/api/simulation/{session_id}/results", headers=headers)
    assert results_res.status_code == 200
    results_json = results_res.json()
    assert "expected_pathway" in results_json
    assert len(results_json["expected_pathway"]) > 0
    assert results_json["expected_pathway"][0]["type"] == "system"
    assert "Daniel Thomas" in results_json["expected_pathway"][0]["label"]


def test_case_specific_critical_mistakes_stroke():
    from evaluation.scorer import evaluate_session_rules
    import uuid

    stroke_case = {
        "title": "Sudden Left-Sided Weakness",
        "specialty": "Emergency Medicine / Neurology",
        "patient": {"name": "Eleanor Vance", "chief_complaint": "Slurred speech and arm weakness"},
        "examinations": [
            {"type": "neurological", "name": "Neurological Examination", "result": "Left facial droop"},
            {"type": "general", "name": "General Physical Examination", "result": "Alert, slurred speech"}
        ],
        "investigations": [
            {"id": "ct_head", "name": "CT Scan of Head", "cost": 350, "result": "Acute ischemic stroke"},
            {"id": "cbc", "name": "Complete Blood Count", "cost": 80, "result": "Normal"}
        ],
        "evaluation_criteria": {
            "correct_diagnosis": "Acute ischemic stroke",
            "correct_subtypes": ["stroke", "ischemic stroke", "acute ischemic stroke"],
            "critical_questions": ["onset_trigger", "associated_symptoms"],
            "required_investigations": ["ct_head"],
            "unnecessary_investigations": ["ct_angio"]
        }
    }

    # Simulate student who only asked generic questions, missed CT Head, missed Neuro exam, and submitted wrong diagnosis
    session = models.SimulationSession(
        id=str(uuid.uuid4()),
        user_id=1,
        case_id="stroke_001",
        status="completed",
        final_diagnosis="Tension Headache",
        immediate_priority="Prescribe paracetamol",
        evidence_justification="Patient has headache and mild fatigue."
    )

    actions = [
        models.StudentAction(session_id=session.id, action_type="question", content="Do you have a family history?", category="family_history"),
        models.StudentAction(session_id=session.id, action_type="examination", content="Requested General Physical Examination", category="general"),
        models.StudentAction(session_id=session.id, action_type="investigation", content="Complete Blood Count", category="cbc"),
    ]

    scores, strengths, weaknesses, critical_mistakes = evaluate_session_rules(session, stroke_case, actions)

    # Verify that mistakes are strictly Stroke-specific and DO NOT mention cardiac/ECG
    mistakes_text = " ".join(critical_mistakes).lower()
    assert "ct scan of head" in mistakes_text
    assert "neurological examination" in mistakes_text
    assert "acute ischemic stroke" in mistakes_text
    assert "tension headache" in mistakes_text
    assert "cardiac" not in mistakes_text
    assert "ecg" not in mistakes_text
    assert "troponin" not in mistakes_text


def test_zero_critical_mistakes_on_perfect_run():
    from evaluation.scorer import evaluate_session_rules
    import uuid

    acs_case = {
        "title": "Chest Discomfort",
        "specialty": "Emergency Medicine / Cardiology",
        "patient": {"name": "Daniel Thomas", "chief_complaint": "Chest pressure"},
        "examinations": [
            {"type": "cardiovascular", "name": "Cardiovascular Examination", "result": "Tachycardia"},
            {"type": "general", "name": "General Physical Examination", "result": "Diaphoretic"}
        ],
        "investigations": [
            {"id": "ecg", "name": "12-Lead Electrocardiogram (ECG)", "cost": 100, "result": "ST Elevation"},
            {"id": "troponin", "name": "Cardiac Troponin I", "cost": 150, "result": "1.85 ng/mL"}
        ],
        "evaluation_criteria": {
            "correct_diagnosis": "Acute coronary syndrome",
            "correct_subtypes": ["acute coronary syndrome", "stemi", "acs"],
            "critical_questions": ["pain_characteristics", "lifestyle_risk_factors"],
            "required_investigations": ["ecg", "troponin"],
            "unnecessary_investigations": ["ct_angio"]
        }
    }

    session = models.SimulationSession(
        id=str(uuid.uuid4()),
        user_id=1,
        case_id="chest_pain_001",
        status="completed",
        final_diagnosis="Acute coronary syndrome",
        immediate_priority="Activate cardiac catheterization lab and aspirin 325mg",
        evidence_justification="ST-elevation and positive troponin."
    )

    actions = [
        models.StudentAction(session_id=session.id, action_type="question", content="Where does the pain radiate?", category="pain_characteristics"),
        models.StudentAction(session_id=session.id, action_type="question", content="Do you smoke?", category="lifestyle_risk_factors"),
        models.StudentAction(session_id=session.id, action_type="examination", content="Requested Cardiovascular Examination", category="cardiovascular"),
        models.StudentAction(session_id=session.id, action_type="investigation", content="12-Lead Electrocardiogram (ECG)", category="ecg"),
        models.StudentAction(session_id=session.id, action_type="investigation", content="Cardiac Troponin I", category="troponin"),
        models.StudentAction(session_id=session.id, action_type="diagnosis_update", content="Updated differentials: ACS (80%), GERD (20%)", category="diagnosis"),
        models.StudentAction(session_id=session.id, action_type="diagnosis_update", content="Updated differentials: Acute STEMI (95%)", category="diagnosis"),
    ]

    scores, strengths, weaknesses, critical_mistakes = evaluate_session_rules(session, acs_case, actions)

    # Perfect run must have 0 critical mistakes
    assert len(critical_mistakes) == 0
    assert scores["history_score"] == 20.0
    assert scores["investigation_score"] == 20.0
    assert scores["resource_efficiency_score"] == 5.0
    assert scores["differential_score"] == 15.0
    assert scores["decision_score"] == 5.0



