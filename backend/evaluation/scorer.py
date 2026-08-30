from typing import List, Dict, Any, Tuple
import json
import models

def evaluate_session_rules(
    session: models.SimulationSession,
    case_data: Dict[str, Any],
    actions: List[models.StudentAction],
    student_disposition: str = None
) -> Tuple[Dict[str, float], List[str], List[str], List[str]]:
    """
    Computes rule-based scores (max 65 points) and flags.
    History Taking: 20 pts
    Investigation Selection: 20 pts
    Resource Efficiency: 5 pts
    Differential Diagnosis Updates: 15 pts
    Final Decision: 5 pts
    
    Total Rules Score: 65 pts.
    """
    history_score = 0.0
    investigation_score = 0.0
    efficiency_score = 5.0
    differential_score = 0.0
    decision_score = 0.0
    
    strengths = []
    weaknesses = []
    critical_mistakes = []
    
    criteria = case_data.get("evaluation_criteria", {})
    correct_diagnosis = criteria.get("correct_diagnosis", "").lower()
    correct_subtypes = criteria.get("correct_subtypes", [])
    critical_categories = criteria.get("critical_questions", [])
    required_investigations = criteria.get("required_investigations", [])
    unnecessary_investigations = criteria.get("unnecessary_investigations", [])
    
    # 1. Evaluate History Taking (Max 20)
    # Count unique critical question categories asked
    asked_categories = set()
    for act in actions:
        if act.action_type == "question" and act.category:
            asked_categories.add(act.category)
            
    matched_critical = [c for c in critical_categories if c in asked_categories]
    history_score = (len(matched_critical) / len(critical_categories)) * 20.0 if critical_categories else 20.0
    
    if len(matched_critical) == len(critical_categories):
        strengths.append("Systematic history taking; gathered all key risk factors and symptoms.")
    else:
        missed = [c.replace("_", " ") for c in critical_categories if c not in asked_categories]
        weaknesses.append(f"Incomplete history taking; did not investigate: {', '.join(missed)}.")
        if len(missed) > 2:
            critical_mistakes.append(f"Failed to systematically ask about critical history factors (missed {len(missed)}).")

    # 2. Evaluate Investigation Selection (Max 20)
    ordered_investigations = set()
    for act in actions:
        if act.action_type == "investigation" and act.category:
            ordered_investigations.add(act.category.lower())
            
    matched_investigations = [i for i in required_investigations if i in ordered_investigations]
    investigation_score = (len(matched_investigations) / len(required_investigations)) * 20.0 if required_investigations else 20.0
    
    if len(matched_investigations) == len(required_investigations):
        strengths.append("Appropriately ordered all high-value standard baseline investigations.")
    else:
        missed_inv = [i.replace("_", " ").upper() for i in required_investigations if i not in ordered_investigations]
        weaknesses.append(f"Missed essential diagnostic tests: {', '.join(missed_inv)}.")
        if missed_inv:
            critical_mistakes.append(f"Failed to order crucial clinical workup tests ({', '.join(missed_inv)}).")

    # 3. Evaluate Resource Efficiency (Max 5)
    # Deduct 2.5 points for each unnecessary test ordered
    wasted_tests = [i for i in unnecessary_investigations if i in ordered_investigations]
    efficiency_score = max(0.0, 5.0 - (len(wasted_tests) * 2.5))
    
    if len(wasted_tests) > 0:
        weaknesses.append(f"Ordered low-yield or unnecessary diagnostics ({', '.join(wasted_tests)}) before standard screening.")
        critical_mistakes.append(f"Incurred unnecessary delay and cost by ordering advanced diagnostics ({', '.join(wasted_tests)}).")
    else:
        strengths.append("Excellent resource management; avoided high-cost unnecessary imaging tests.")

    # 4. Evaluate Differential Diagnosis Updates (Max 15)
    # Count updates
    update_count = sum(1 for act in actions if act.action_type == "diagnosis_update")
    if update_count >= 2:
        differential_score = 15.0
        strengths.append("Consistently updated differential diagnoses as new clinical data arrived.")
    elif update_count == 1:
        differential_score = 10.0
        weaknesses.append("Updated hypothesis only once; consider continuous reassessment as evidence changes.")
    else:
        differential_score = 0.0
        weaknesses.append("Never updated differential diagnoses during the investigation.")

    # 5. Evaluate Final Decision (Max 5)
    final_diag_str = (session.final_diagnosis or "").lower()
    is_correct = False
    for subtype in correct_subtypes:
        if subtype in final_diag_str:
            is_correct = True
            break
            
    if is_correct:
        decision_score = 5.0
        strengths.append(f"Correctly identified final diagnosis: {session.final_diagnosis}.")
    else:
        decision_score = 0.0
        weaknesses.append(f"Incorrect final diagnosis. Submitted: '{session.final_diagnosis}', expected: '{correct_diagnosis}'.")
        critical_mistakes.append(f"Failed to correctly diagnose the primary condition: {correct_diagnosis}.")

    # 6. Evaluate Disposition / Referral Triage (Max 5, but separate logic)
    disposition_score = 0.0
    correct_disposition = None
    if session.facility_tier in ["phc", "chc"]:
        referral_criteria = criteria.get("referral_criteria", {})
        if referral_criteria:
            correct_disposition = referral_criteria.get("correct_disposition_by_tier", {}).get(session.facility_tier)
            if correct_disposition and student_disposition:
                if student_disposition.lower() == correct_disposition.lower():
                    disposition_score = 5.0
                    if student_disposition.lower() == "refer":
                        strengths.append(f"Correctly recognized the limits of {session.facility_tier.upper()} tier and made a safe disposition decision to refer.")
                    else:
                        strengths.append(f"Correctly decided to manage locally at {session.facility_tier.upper()} tier instead of over-referring.")
                else:
                    if correct_disposition.lower() == "refer":
                        critical_mistakes.append(f"Attempted to manage a case requiring referral at a facility ({session.facility_tier.upper()}) without the resources to safely do so.")
                    else:
                        weaknesses.append(f"Referred a case that could have reasonably been managed locally at {session.facility_tier.upper()} tier.")

    # Return new fields inside the dictionary alongside the existing tuples
    scores = {
        "history_score": round(history_score, 1),
        "investigation_score": round(investigation_score, 1),
        "resource_efficiency_score": round(efficiency_score, 1),
        "differential_score": round(differential_score, 1),
        "decision_score": round(decision_score, 1),
        "disposition_score": round(disposition_score, 1),
        "disposition_correct": student_disposition or "",
        "disposition_expected": correct_disposition or "",
    }
    return scores, strengths, weaknesses, critical_mistakes
