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

