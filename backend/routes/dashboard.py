from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime
from typing import Dict, Any

from database import get_db
from routes.auth import get_current_user
import models
import schemas

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def calculate_streak(sessions) -> int:
    if not sessions:
        return 0
        
    # Get distinct completion dates in sorted order (newest first)
    dates = sorted(
        list(set(s.completed_at.date() for s in sessions if s.completed_at)), 
        reverse=True
    )
    if not dates:
        return 0
        
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    # If the user hasn't completed a case today or yesterday, streak is broken
    if dates[0] != today and dates[0] != yesterday:
        return 0
        
    streak = 1
    for i in range(len(dates) - 1):
        diff = dates[i] - dates[i+1]
        if diff.days == 1:
            streak += 1
        elif diff.days > 1:
            break # Streak broken in past
            
    return streak

@router.get("", response_model=schemas.DashboardStatsOut)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 1. Fetch user sessions
    user_sessions = db.query(models.SimulationSession).filter(
        models.SimulationSession.user_id == current_user.id
    ).all()
    
    completed_sessions = [s for s in user_sessions if s.status == "completed"]
    cases_completed = len(completed_sessions)
    
    # 2. Average and Best scores
    evals = db.query(models.Evaluation).join(
        models.SimulationSession, models.SimulationSession.id == models.Evaluation.session_id
    ).filter(
        models.SimulationSession.user_id == current_user.id
    ).all()
    
    avg_score = 0.0
    best_score = 0.0
    
    if evals:
        scores = [e.final_score for e in evals]
        avg_score = round(sum(scores) / len(scores), 1)
        best_score = max(scores)
        
    # 3. Calculate streak
    streak = calculate_streak(completed_sessions)
    
    # 4. Recent simulations (last 5)
    recent = []
    # Query with join to Case
    sessions_query = db.query(models.SimulationSession, models.Case).join(
        models.Case, models.Case.id == models.SimulationSession.case_id
    ).filter(
        models.SimulationSession.user_id == current_user.id
    ).order_by(models.SimulationSession.created_at.desc()).limit(5).all()
    
    for sess, case in sessions_query:
        # Get evaluation score if completed
        score_val = None
        eval_rec = db.query(models.Evaluation).filter(models.Evaluation.session_id == sess.id).first()
        if eval_rec:
            score_val = eval_rec.final_score
            
        recent.append({
            "session_id": sess.id,
            "case_id": case.id,
            "title": case.title,
            "specialty": case.specialty,
            "difficulty": case.difficulty,
            "status": sess.status,
            "score": score_val,
            "created_at": sess.created_at.isoformat()
        })
        
    # 5. Average scores by category
    cat_scores = {
        "History Taking": 0.0,
        "Differential Diagnosis": 0.0,
        "Investigation Selection": 0.0,
        "Evidence Interpretation": 0.0,
        "Clinical Reasoning": 0.0,
    }

    if evals:
        cat_scores["History Taking"] = round(sum((e.history_score / 20.0) * 100 for e in evals) / len(evals), 1)
        cat_scores["Differential Diagnosis"] = round(sum((getattr(e, "differential_score", 0) / 15.0) * 100 for e in evals) / len(evals), 1)
        cat_scores["Investigation Selection"] = round(sum((e.investigation_score / 20.0) * 100 for e in evals) / len(evals), 1)
        cat_scores["Evidence Interpretation"] = round(sum((e.evidence_interpretation_score / 20.0) * 100 for e in evals) / len(evals), 1)
        cat_scores["Clinical Reasoning"] = round(sum((e.reasoning_score / 15.0) * 100 for e in evals) / len(evals), 1)

    # 6. Formulate Recommendation based on lowest score
    recommendation = None
    if evals:
        lowest_cat = min(cat_scores, key=cat_scores.get)
        lowest_val = cat_scores[lowest_cat]
        if lowest_val < 85:
            if lowest_cat == "Investigation Selection":
                recommendation = "Your investigation selection score is lower than your other categories. Try an Emergency Medicine case focused on prioritization."
            elif lowest_cat == "History Taking":
                recommendation = "Your history taking score is lower. Try a case focused on systematic patient interviews and risk factors identification."
            elif lowest_cat == "Evidence Interpretation":
                recommendation = "Your evidence interpretation score is lower. Focus on reviewing ECGs and lab values thoroughly before making decisions."
            elif lowest_cat == "Clinical Reasoning":
                recommendation = "Your clinical reasoning score is lower. Work on updating your differential diagnosis dynamically as new evidence appears."
            elif lowest_cat == "Differential Diagnosis":
                recommendation = "Your differential diagnosis score is lower. Practice updating your hypothesis list as new evidence arrives."
            else:
                recommendation = "Keep practicing! Focus on areas with lower scores to improve your diagnostic performance."
        else:
            recommendation = "Excellent performance across all categories! Try an Advanced difficulty case to push your limits."
    else:
        recommendation = "Welcome to DiagnOS! Select the 'Atypical Chest Pain' case in the Case Library to start your first clinical simulation."
        
    return {
        "cases_completed": cases_completed,
        "average_score": avg_score,
        "best_score": best_score,
        "streak": streak,
        "recent_simulations": recent,
        "category_scores": cat_scores,
        "recommendation": recommendation
    }
