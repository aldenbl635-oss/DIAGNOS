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
from evaluation.ai_eval import evaluate_clinical_reasoning

router = APIRouter(prefix="/simulation", tags=["Simulation"])

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

    patient = case_data.get("patient", {})
    chief_complaint = patient.get("chief_complaint", "not feeling well")
    greeting = (
        f"Hello doctor. I've been feeling this really uncomfortable {chief_complaint.lower()} "
        f"for about 30 minutes now. I'm not sure what's going on..."
        if chief_complaint else "Hello doctor."
    )
    chat_messages.append({"role": "patient", "text": greeting, "category": None})

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
            chat_messages.append({
                "role": "patient",
                "text": act.content,
                "category": act.category
            })
            chat_history.append({"role": "patient", "text": act.content})
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

    return {
        "session": session,
        "case": build_case_detail(case),
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
    session = models.SimulationSession(
        id=session_id,
        user_id=current_user.id,
        case_id=case.id,
        remaining_resources=1000,
        elapsed_seconds=0,
        status="in_progress",
        differential_diagnoses=[]
    )
    db.add(session)
    
    # Log starting action
    start_action = models.StudentAction(
        session_id=session_id,
        action_type="system",
        content=f"Assessment started: {case.title}. Chief Complaint: {case.data['patient']['chief_complaint']}.",
        cost=0,
        category="system"
    )
    db.add(start_action)
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
    
    # Retrieve past student actions for chat context
    past_actions = db.query(models.StudentAction).filter(
        models.StudentAction.session_id == session_id,
        models.StudentAction.action_type == "question"
    ).order_by(models.StudentAction.timestamp.asc()).all()
    
    chat_history = []
    for act in past_actions:
        # Extract student question and parser response if structured
        # Content might be saved as a concatenated string or JSON. We save questions directly
        # So we can construct a fake history
        chat_history.append({"role": "student", "text": act.content})
        # Let's search if there's a corresponding system response in the future, or we just rely on standard prompt formatting.
        # To simplify, we can format the user questions.
    
    # Run patient simulation
    answer, category = simulate_patient(payload.question, case_data, chat_history)
    
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
    response_action = models.StudentAction(
        session_id=session_id,
        action_type="patient_response",
        content=answer,
        cost=0,
        category=category
    )
    db.add(response_action)
    db.commit()
    db.refresh(session)
    
    return {
        "answer": answer,
        "category": category,
        "remaining_resources": session.remaining_resources,
        "elapsed_seconds": session.elapsed_seconds
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
        "elapsed_seconds": session.elapsed_seconds
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
        
    cost = selected_inv.get("cost", 0)
    
    # Check budget
    if session.remaining_resources < cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Insufficient resources. Wording this test requires {cost} credits, but you only have {session.remaining_resources} credits remaining."
        )
        
    # Deduct cost and update time
    session.remaining_resources -= cost
    session.elapsed_seconds += 120 # +2 minutes (120 seconds) for ordering test
    
    # Record action
    log_action = models.StudentAction(
        session_id=session_id,
        action_type="investigation",
        content=selected_inv.get("name"),
        cost=cost,
        category=payload.investigation_id
    )
    db.add(log_action)
    db.commit()
    db.refresh(session)
    
    return {
        "investigation_id": selected_inv.get("id"),
        "name": selected_inv.get("name"),
        "cost": cost,
        "result": selected_inv.get("result"),
        "interpretation": selected_inv.get("interpretation"),
        "remaining_resources": session.remaining_resources,
        "elapsed_seconds": session.elapsed_seconds
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
            return {
                "session": session,
                "evaluation": eval_record,
                "actions": actions
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
    evaluation = evaluate_clinical_reasoning(session, case.data, actions)
    
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    db.refresh(session)
    
    return {
        "session": session,
        "evaluation": evaluation,
        "actions": actions
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
    
    return {
        "session": session,
        "evaluation": evaluation,
        "actions": actions
    }
