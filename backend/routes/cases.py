from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from routes.auth import get_current_user
import models
import schemas

router = APIRouter(prefix="/cases", tags=["Cases"])

def build_case_brief(c: models.Case) -> dict:
    patient = c.data.get("patient", {})
    presentation = c.data.get("presentation", {})
    chief_complaint = presentation.get("chief_complaint") or patient.get("chief_complaint", "Unknown")
    return {
        "id": c.id,
        "title": c.title,
        "specialty": c.specialty,
        "difficulty": c.difficulty,
        "duration_mins": c.duration_mins,
        "patient_age": patient.get("age") or c.data.get("patient_age", 0),
        "patient_sex": patient.get("sex") or c.data.get("patient_sex", "Unknown"),
        "chief_complaint": chief_complaint,
    }

def build_case_detail(c: models.Case) -> dict:
    patient = c.data.get("patient", {})
    presentation = c.data.get("presentation", {})
    vitals = c.data.get("vitals") or patient.get("vitals", {})
    brief = build_case_brief(c)
    return {
        **brief,
        "patient_name": patient.get("name", "Unknown Patient"),
        "vitals": {
            "bp": vitals.get("bp", "N/A"),
            "hr": vitals.get("hr", "N/A"),
            "spo2": vitals.get("spo2", "N/A"),
            "temp": vitals.get("temp", "N/A"),
        },
        "examinations": [
            {"type": ex.get("type"), "name": ex.get("name")}
            for ex in c.data.get("examinations", [])
        ],
        "investigations": [
            {
                "id": inv.get("id"),
                "name": inv.get("name"),
                "cost": inv.get("cost", 0),
                "category": inv.get("category", "OTHER"),
                "available_at": inv.get("available_at", ["tertiary", "chc", "phc"]),
            }
            for inv in c.data.get("investigations", [])
        ],
        "differential_options": c.data.get("differential_diagnoses", []),
        "initial_briefing": patient.get("initial_briefing") or presentation.get("initial_briefing", ""),
    }

@router.get("", response_model=List[schemas.CaseBriefOut])
def get_cases(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Find case IDs that the user has already attended
    attended = db.query(models.SimulationSession.case_id).filter(
        models.SimulationSession.user_id == current_user.id
    ).all()
    attended_ids = {row[0] for row in attended}

    db_cases = db.query(models.Case).all()
    # Filter out already attended case variants
    unattended_cases = []
    
    for c in db_cases:
        if c.id not in attended_ids:
            # Check specialization match
            if not current_user.specialization or current_user.specialization.lower() in c.specialty.lower():
                unattended_cases.append(c)
                
    return [build_case_brief(c) for c in unattended_cases]

@router.get("/{case_id}", response_model=schemas.CaseDetailOut)
def get_case(case_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    c = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    return build_case_detail(c)
