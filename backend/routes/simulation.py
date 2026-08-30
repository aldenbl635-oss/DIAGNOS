import uuid
import datetime
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from database import get_db
from routes.auth import get_current_user
from routes.cases import build_case_detail
import models
import schemas
from ai.simulator import simulate_patient
from ai.patient_agent import PatientAgent
from ai.patient_state import PatientAgentState
from evaluation.ai_eval import evaluate_clinical_reasoning

router = APIRouter(prefix="/simulation", tags=["Simulation"])

def get_dynamic_vitals(base_vitals: dict, emotion_dict: dict, case_data: dict = None) -> dict:
    import re
    hr_str = base_vitals.get("hr", "")
    bp_str = base_vitals.get("bp", "")
    
    hr_match = re.search(r"\d+", hr_str)
    hr_base = int(hr_match.group(0)) if hr_match else 75
    
    bp_match = re.findall(r"\d+", bp_str)
    if len(bp_match) >= 2:
        sys_base, dia_base = int(bp_match[0]), int(bp_match[1])
    else:
        sys_base, dia_base = 120, 80
        
    # Get current emotions, default to baseline if not provided
    anxiety = emotion_dict.get("anxiety", 60)
    fear = emotion_dict.get("fear", 35)
    anger = emotion_dict.get("anger", 10)
    trust = emotion_dict.get("trust", 60)
    pain = emotion_dict.get("pain", 45)
    
    # Calculate current stress index (incorporating physical pain and emotions)
    stress_index = (anxiety * 0.35 + fear * 0.35 + anger * 0.15 + pain * 0.15 - (trust - 50) * 0.20)
    
    # Calculate baseline stress index dynamically based on case config/personality if available
    baseline_stress_index = 39.5
    
    if case_data:
        personality_data = case_data.get("patient_personality") or case_data.get("personality", {})
        from ai.patient_personality import PersonalityProfile
        personality = PersonalityProfile.from_dict(personality_data)
        
        base_anxiety = min(100, personality.baseline_anxiety + 10)
        base_fear = max(0, personality.baseline_anxiety - 15)
        base_anger = 10
        base_trust = max(20, 100 - personality.distrust_of_medical - 10)
        
        base_pain = 45
        history_of_illness = case_data.get("clinical_facts", {}).get("history_of_illness", [])
        for line in history_of_illness:
            if "severity" in line.lower() or "pain" in line.lower():
                match = re.search(r"(\d+)\s*/\s*10", line)
                if match:
                    base_pain = int(match.group(1)) * 10
                    break
        
        baseline_stress_index = (base_anxiety * 0.35 + base_fear * 0.35 + base_anger * 0.15 + base_pain * 0.15 - (base_trust - 50) * 0.20)
    
    # Compute stress delta relative to baseline
    stress_delta = stress_index - baseline_stress_index
    
    # Map stress delta to vitals changes dynamically
    dynamic_hr = int(hr_base + stress_delta * 1.2)
    dynamic_hr = max(60, min(150, dynamic_hr))
    
    dynamic_sys = int(sys_base + stress_delta * 1.0)
    dynamic_sys = max(90, min(200, dynamic_sys))
    
    dynamic_dia = int(dia_base + stress_delta * 0.6)
    dynamic_dia = max(60, min(120, dynamic_dia))
    
    # Include dynamic respiratory rate (rr) based on stress/pain (standard baseline RR 18)
    rr_base = 18
    dynamic_rr = int(rr_base + stress_delta * 0.25)
    dynamic_rr = max(12, min(30, dynamic_rr))
    
    return {
        "bp": f"{dynamic_sys}/{dynamic_dia} mmHg" if "mmHg" in bp_str or not bp_str else f"{dynamic_sys}/{dynamic_dia}",
        "hr": f"{dynamic_hr} bpm" if "bpm" in hr_str or not hr_str else f"{dynamic_hr}",
        "rr": f"{dynamic_rr}",
        "spo2": base_vitals.get("spo2", "96%"),
        "temp": base_vitals.get("temp", "36.8°C"),
    }

def get_user_session(session_id: str, user_id: int, db: Session) -> models.SimulationSession:
    session = db.query(models.SimulationSession).filter(
        models.SimulationSession.id == session_id,
        models.SimulationSession.user_id == user_id
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session

def rebuild_workspace_state(
    session: models.SimulationSession,
    case_data: Dict[str, Any],
    actions: List[models.StudentAction]
) -> Dict[str, Any]:
    """Reconstruct chat and panel state from persisted action logs."""
    chat_messages: List[Dict[str, Any]] = []
    exams_revealed: Dict[str, str] = {}
    investigations_ordered: Dict[str, Dict[str, Any]] = {}

    exam_lookup = {ex.get("type"): ex for ex in case_data.get("examinations", [])}
    inv_lookup = {inv.get("id"): inv for inv in case_data.get("investigations", [])}

    from ai.offline_responder import OfflinePatientResponder
    responder = OfflinePatientResponder(case_data)
    greeting = responder.generate_greeting()
    
    # Initialize state to extract the patient's starting emotion and cue
    if session.patient_agent_state:
        agent_state = PatientAgentState.from_dict(session.patient_agent_state, case_data)
    else:
        agent_state = PatientAgentState.initialize_from_case(case_data)
    
    g_label = agent_state.emotion.get_label()
    g_cue = agent_state.emotion.get_behavioral_cue()
    
    chat_messages.append({
        "role": "patient",
        "text": greeting,
        "category": None,
        "emotion_label": g_label,
        "emotional_cue": g_cue,
        "communication_state": g_label.lower()
    })

    has_patient_responses = any(a.action_type == "patient_response" for a in actions)
    chat_history: List[Dict[str, str]] = []

    for act in actions:
        if act.action_type == "system":
            continue

        if act.action_type == "question":
            chat_messages.append({"role": "student", "text": act.content, "category": None})
            if not has_patient_responses:
                answer, category = simulate_patient(act.content, case_data, chat_history)
                chat_messages.append({"role": "patient", "text": answer, "category": category})
            chat_history.append({"role": "student", "text": act.content})
            continue

        if act.action_type == "patient_response":
            text = act.content
            emotion_label = None
            emotional_cue = None
            communication_state = None
            
            try:
                import json
                payload = json.loads(act.content)
                if isinstance(payload, dict) and "text" in payload:
                    text = payload.get("text", "")
                    emotion_label = payload.get("emotion_label")
                    emotional_cue = payload.get("emotional_cue")
                    communication_state = payload.get("communication_state")
            except json.JSONDecodeError:
                pass
                
            chat_messages.append({
                "role": "patient",
                "text": text,
                "category": act.category,
                "emotion_label": emotion_label,
                "emotional_cue": emotional_cue,
                "communication_state": communication_state,
            })
            chat_history.append({"role": "patient", "text": text})
            continue

        if act.action_type == "examination" and act.category:
            exam = exam_lookup.get(act.category, {})
            exams_revealed[act.category] = exam.get("result", "No findings recorded.")
            continue

        if act.action_type == "investigation" and act.category:
            inv = inv_lookup.get(act.category, {})
            investigations_ordered[act.category] = {
                "name": inv.get("name", act.content),
                "cost": act.cost or inv.get("cost", 0),
                "result": inv.get("result", ""),
                "interpretation": inv.get("interpretation", ""),
            }

    return {
        "chat_messages": chat_messages,
        "exams_revealed": exams_revealed,
        "investigations_ordered": investigations_ordered,
    }

@router.get("/{session_id}", response_model=schemas.SimulationSessionDetailOut)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    session = get_user_session(session_id, current_user.id, db)
    case = db.query(models.Case).filter(models.Case.id == session.case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    actions = db.query(models.StudentAction).filter(
        models.StudentAction.session_id == session_id
    ).order_by(models.StudentAction.timestamp.asc()).all()

    workspace = rebuild_workspace_state(session, case.data, actions)

    case_detail = build_case_detail(case)
    if session.patient_agent_state:
        current_emotion = session.patient_agent_state.get("emotion", {})
        case_detail["vitals"] = get_dynamic_vitals(case.data.get("patient", {}).get("vitals", {}), current_emotion, case.data)

    return {
        "session": session,
        "case": case_detail,
        "actions": actions,
        **workspace,
    }

@router.post("/start", response_model=schemas.SimulationSessionOut)
def start_simulation(
    payload: schemas.SimulationStart,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    case = db.query(models.Case).filter(models.Case.id == payload.case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
        
    session_id = str(uuid.uuid4())
    agent_state = PatientAgentState.initialize_from_case(case.data)
    session = models.SimulationSession(
        id=session_id,
        user_id=current_user.id,
        case_id=case.id,
        facility_tier=payload.facility_tier,
        remaining_resources=1000,
        elapsed_seconds=0,
        status="in_progress",
        differential_diagnoses=[],
        patient_agent_state=agent_state.to_dict()
    )
    db.add(session)
    
    start_action = models.StudentAction(
        session_id=session_id,
        action_type="system",
        content=f"Assessment started: {case.title}. Chief Complaint: {case.data['patient']['chief_complaint']}.",
        cost=0,
        category="system"
    )
    db.add(start_action)

    # 12. Fix the initial patient greeting: Generate it from case data immediately
    patient_data = case.data.get("patient", {})
    init_briefing = patient_data.get("initial_statement", "")
    if not init_briefing:
        init_briefing = case.data.get("presentation", {}).get("initial_briefing", "")
    if not init_briefing:
        init_briefing = f"Hello doctor... I came in because of my {patient_data.get('chief_complaint', 'condition')}."
    elif not init_briefing.lower().startswith("hello"):
        init_briefing = f"Hello doctor. {init_briefing}"
        
    import json
    greeting_action = models.StudentAction(
        session_id=session_id,
        action_type="patient_response",
        content=json.dumps({
            "text": init_briefing,
            "emotion_label": "Anxious",
            "emotional_cue": "The patient shifts uncomfortably.",
            "communication_state": "anxious"
        }),
        cost=0,
        category="system"
    )
    db.add(greeting_action)
    db.commit()
    db.refresh(session)
    return session

@router.post("/{session_id}/question", response_model=schemas.QuestionResponse)
def ask_question(
    session_id: str,
    payload: schemas.QuestionSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    session = db.query(models.SimulationSession).filter(
        models.SimulationSession.id == session_id,
        models.SimulationSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Simulation already completed")

    case = db.query(models.Case).filter(models.Case.id == session.case_id).first()
    case_data = case.data

    # Load or initialize patient agent state
    if session.patient_agent_state:
        agent_state = PatientAgentState.from_dict(session.patient_agent_state, case_data)
    else:
        agent_state = PatientAgentState.initialize_from_case(case_data)
    
    # Retrieve past student actions for chat context
    past_actions = db.query(models.StudentAction).filter(
        models.StudentAction.session_id == session_id,
        models.StudentAction.action_type.in_(["question", "patient_response"])
    ).order_by(models.StudentAction.timestamp.asc()).all()
    
    chat_history = []
    for act in past_actions:
        role = "student" if act.action_type == "question" else "patient"
        chat_history.append({"role": role, "text": act.content})

    # Run PatientAgent
    agent = PatientAgent(case_data)
    updated_state, output = agent.generate_response(
        state=agent_state,
        conversation_history=chat_history,
        student_message=payload.question
    )

    # Persist updated agent state to session
    session.patient_agent_state = updated_state.to_dict()

    import json
    from ai.patient_reasoning import map_revealed_fact_to_category
    
    answer = output.get("response", "")
    revealed = output.get("revealed_information", [])
    category = map_revealed_fact_to_category(revealed[0] if revealed else "other")

    # Update session time and resources
    session.elapsed_seconds += 15 # +15 seconds per question
    
    # Record question action
    log_action = models.StudentAction(
        session_id=session_id,
        action_type="question",
        content=payload.question,
        cost=0,
        category=category
    )
    db.add(log_action)

    # Persist patient response for session resume
    response_content = json.dumps({
        "text": answer,
        "emotion_label": output.get("emotion_label"),
        "emotional_cue": output.get("emotional_cue"),
        "communication_state": output.get("communication_state"),
    })

    response_action = models.StudentAction(
        session_id=session_id,
        action_type="patient_response",
        content=response_content,
        cost=0,
        category=category
    )
    db.add(response_action)
    db.commit()
    db.refresh(session)
    
    dynamic_vitals_dict = get_dynamic_vitals(case_data.get("patient", {}).get("vitals", {}), updated_state.emotion.to_dict())

    return {
        "answer": answer,
        "category": category,
        "remaining_resources": session.remaining_resources,
        "elapsed_seconds": session.elapsed_seconds,
        "emotion_label": output.get("emotion_label"),
        "emotional_cue": output.get("emotional_cue"),
        "communication_state": output.get("communication_state"),
        "vitals": dynamic_vitals_dict
    }

@router.post("/{session_id}/examination", response_model=schemas.ExamResponse)
def perform_examination(
    session_id: str,
    payload: schemas.ExamSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    session = db.query(models.SimulationSession).filter(
        models.SimulationSession.id == session_id,
        models.SimulationSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Simulation already completed")

    case = db.query(models.Case).filter(models.Case.id == session.case_id).first()
    exams = case.data.get("examinations", [])
    
    result = "No findings recorded for this examination type."
    exam_name = payload.examination_type
    for ex in exams:
        if ex.get("type") == payload.examination_type:
            result = ex.get("result")
            exam_name = ex.get("name")
            break
            
    # Load or initialize patient agent state
    import json
    if session.patient_agent_state:
        agent_state = PatientAgentState.from_dict(session.patient_agent_state, case.data)
    else:
        agent_state = PatientAgentState.initialize_from_case(case.data)

    patient_reaction = None
    if agent_state.emotion.anxiety > 40:
        patient_reaction = f"Ouch... please be gentle, doctor. My chest feels really tight right now, doing {exam_name.lower()} is a bit uncomfortable."
        agent_state.memory.add_event(f"examination_performed_{payload.examination_type}", importance=0.4, category="clinical")
        
        # Persist patient response for session resume
        response_content = json.dumps({
            "text": patient_reaction,
            "emotion_label": agent_state.emotion.get_label(),
            "emotional_cue": agent_state.emotion.get_behavioral_cue(),
            "communication_state": agent_state.emotion.get_label().lower(),
        })

        response_action = models.StudentAction(
            session_id=session_id,
            action_type="patient_response",
            content=response_content,
            cost=0,
            category=payload.examination_type
        )
        db.add(response_action)
        
    session.patient_agent_state = agent_state.to_dict()

    # Update time
    session.elapsed_seconds += 45 # +45 seconds for physical examination
    
    # Record action
    log_action = models.StudentAction(
        session_id=session_id,
        action_type="examination",
        content=f"Requested {exam_name}.",
        cost=0,
        category=payload.examination_type
    )
    db.add(log_action)
    db.commit()
    db.refresh(session)
    
    return {
        "result": result,
        "remaining_resources": session.remaining_resources,
        "elapsed_seconds": session.elapsed_seconds,
        "patient_reaction": patient_reaction
    }

@router.post("/{session_id}/investigation", response_model=schemas.InvestigationResponse)
def order_investigation(
    session_id: str,
    payload: schemas.InvestigationSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    session = db.query(models.SimulationSession).filter(
        models.SimulationSession.id == session_id,
        models.SimulationSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Simulation already completed")

    case = db.query(models.Case).filter(models.Case.id == session.case_id).first()
    investigations = case.data.get("investigations", [])
    
    selected_inv = None
    for inv in investigations:
        if inv.get("id") == payload.investigation_id:
            selected_inv = inv
            break
            
    if not selected_inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found in this case")
        
    available_at = selected_inv.get("available_at", ["tertiary", "chc", "phc"])
    if session.facility_tier not in available_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Investigation not available at {session.facility_tier.upper()} tier"
        )
        
    cost = selected_inv.get("cost", 0)
    
    # Check budget
    if session.remaining_resources < cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Insufficient resources. Ordering this test requires {cost} credits, but you only have {session.remaining_resources} credits remaining."
        )
        
    # Deduct cost and update time
    session.remaining_resources -= cost
    session.elapsed_seconds += 120 # +2 minutes (120 seconds) for ordering test
    
    # Record ordering action
    log_action = models.StudentAction(
        session_id=session_id,
        action_type="investigation",
        content=selected_inv.get("name"),
        cost=cost,
        category=payload.investigation_id
    )
    db.add(log_action)

    # Rebuild state and generate patient reaction
    import json
    if session.patient_agent_state:
        agent_state = PatientAgentState.from_dict(session.patient_agent_state, case.data)
    else:
        agent_state = PatientAgentState.initialize_from_case(case.data)

    agent = PatientAgent(case.data)
    updated_state, patient_reaction = agent.generate_investigation_reaction(agent_state, selected_inv.get("name"))
    
    if patient_reaction:
        # Record patient response log action so it appears in the chat
        response_content = json.dumps({
            "text": patient_reaction,
            "emotion_label": updated_state.emotion.get_label(),
            "emotional_cue": updated_state.emotion.get_behavioral_cue(),
            "communication_state": updated_state.emotion.get_label().lower(),
        })

        response_action = models.StudentAction(
            session_id=session_id,
            action_type="patient_response",
            content=response_content,
            cost=0,
            category=payload.investigation_id
        )
        db.add(response_action)
        
    session.patient_agent_state = updated_state.to_dict()
    db.commit()
    db.refresh(session)
    
    return {
        "investigation_id": selected_inv.get("id"),
        "name": selected_inv.get("name"),
        "cost": cost,
        "result": selected_inv.get("result"),
        "interpretation": selected_inv.get("interpretation"),
        "remaining_resources": session.remaining_resources,
        "elapsed_seconds": session.elapsed_seconds,
        "patient_reaction": patient_reaction
    }

@router.post("/{session_id}/diagnosis", response_model=schemas.SimulationSessionOut)
def update_differential_diagnosis(
    session_id: str,
    payload: schemas.DiagnosisUpdateSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    session = db.query(models.SimulationSession).filter(
        models.SimulationSession.id == session_id,
        models.SimulationSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Simulation already completed")

    # Update state
    session.differential_diagnoses = payload.differential_diagnoses
    
    # Formulate action text
    diags_text = ", ".join([f"{d.get('diagnosis')}: {d.get('confidence')}%" for d in payload.differential_diagnoses])
    
    # Record action
    log_action = models.StudentAction(
        session_id=session_id,
        action_type="diagnosis_update",
        content=f"Updated differentials: [{diags_text}]",
        cost=0,
        category="differentials"
    )
    db.add(log_action)
    db.commit()
    db.refresh(session)
    return session

@router.post("/{session_id}/evaluate", response_model=schemas.SimulationResultOut)
def submit_and_evaluate(
    session_id: str,
    payload: schemas.FinalDiagnosisSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    session = db.query(models.SimulationSession).filter(
        models.SimulationSession.id == session_id,
        models.SimulationSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status == "completed":
        # Check if already evaluated, if yes just return the evaluation
        eval_record = db.query(models.Evaluation).filter(models.Evaluation.session_id == session_id).first()
        actions = db.query(models.StudentAction).filter(models.StudentAction.session_id == session_id).all()
        if eval_record:
            case = db.query(models.Case).filter(models.Case.id == session.case_id).first()
            return {
                "session": session,
                "evaluation": eval_record,
                "actions": actions,
                "case_data": case.data if case else {}
            }
            
    # Update final entries
    session.final_diagnosis = payload.final_diagnosis
    session.immediate_priority = payload.immediate_priority
    session.evidence_justification = payload.evidence_justification
    session.status = "completed"
    session.completed_at = datetime.datetime.now(timezone.utc)
    
    # Get all action logs
    actions = db.query(models.StudentAction).filter(models.StudentAction.session_id == session_id).order_by(models.StudentAction.timestamp.asc()).all()
    
    case = db.query(models.Case).filter(models.Case.id == session.case_id).first()
    
    # Perform scoring (rule-based + AI feedback integration)
    evaluation = evaluate_clinical_reasoning(session, case.data, actions, disposition=payload.disposition)
    
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    db.refresh(session)
    
    return {
        "session": session,
        "evaluation": evaluation,
        "actions": actions,
        "case_data": case.data if case else {}
    }

@router.get("/{session_id}/results", response_model=schemas.SimulationResultOut)
def get_results(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    session = db.query(models.SimulationSession).filter(
        models.SimulationSession.id == session_id,
        models.SimulationSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
    evaluation = db.query(models.Evaluation).filter(models.Evaluation.session_id == session_id).first()
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation results not generated yet")
        
    actions = db.query(models.StudentAction).filter(models.StudentAction.session_id == session_id).order_by(models.StudentAction.timestamp.asc()).all()
    
    case = db.query(models.Case).filter(models.Case.id == session.case_id).first()
    
    return {
        "session": session,
        "evaluation": evaluation,
        "actions": actions,
        "case_data": case.data if case else {}
    }


@router.post("/reset-history")
def reset_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Deletes all simulation sessions (and cascaded elements) for the current user."""
    db.query(models.SimulationSession).filter(
        models.SimulationSession.user_id == current_user.id
    ).delete(synchronize_session=False)
    db.commit()
    return {"message": "Simulation history reset successfully"}


@router.get("/data-sources/status")
def get_data_sources_status(current_user: models.User = Depends(get_current_user)):
    from data.adapters import DialogueDatasetAdapter, ClinicalDatasetAdapter, DecisionMakingAdapter, SyntheticBehaviorAdapter
    
    dialogue = DialogueDatasetAdapter()
    clinical = ClinicalDatasetAdapter()
    decision = DecisionMakingAdapter()
    synthetic = SyntheticBehaviorAdapter()
    
    return {
        "sources": [
            {
                "id": "mimic_iv",
                "name": "MIMIC-IV / MIMIC-IV-ED Vitals & Notes",
                "category": "Clinical Grounding",
                "status": clinical.get_status(),
                "description": "De-identified clinical health data detailing patient demographics, admissions, and vitals."
            },
            {
                "id": "meddialog",
                "name": "MedDialog / NoteChat Medical Dialogue",
                "category": "Dialogue Modeling",
                "status": dialogue.get_status(),
                "description": "Doctor-patient conversation transcripts for guiding conversational naturalness and patient phrasing."
            },
            {
                "id": "decision_making",
                "name": "MIMIC-IV-Ext Clinical Decisions",
                "category": "Sequential Reasoning",
                "status": decision.get_status(),
                "description": "Structured pathway sequence logs to evaluate diagnostic workflow efficiency and timing."
            },
            {
                "id": "synthetic_behavior",
                "name": "Synthetic Patient-Behavior Log",
                "category": "Emotional Reactions",
                "status": synthetic.get_status(),
                "description": "Local behavioral templates mapping doctor communication style to patient state transitions."
            }
        ]
    }

