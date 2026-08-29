from typing import List, Dict, Any, Tuple
import json
import models

QUESTION_CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    "pain_characteristics": "symptom onset, location, character, and pain radiation",
    "lifestyle_risk_factors": "lifestyle risk factors (e.g. smoking, alcohol, diet, activity)",
    "past_medical_history": "past medical history and pre-existing conditions",
    "associated_symptoms": "associated symptoms and red-flag features",
    "family_history": "family medical history",
    "medications": "current medications and drug allergies",
    "onset_trigger": "symptom onset and precipitating triggers",
    "duration": "symptom duration and progression timeline",
    "severity": "symptom severity and functional impact",
}

def evaluate_session_rules(
    session: models.SimulationSession,
    case_data: Dict[str, Any],
    actions: List[models.StudentAction]
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
    
    strengths: List[str] = []
    weaknesses: List[str] = []
    critical_mistakes: List[str] = []
    
    criteria = case_data.get("evaluation_criteria", {})
    correct_diagnosis = criteria.get("correct_diagnosis", "")
    correct_subtypes = criteria.get("correct_subtypes", [])
    critical_categories = criteria.get("critical_questions", [])
    required_investigations = criteria.get("required_investigations", [])
    unnecessary_investigations = criteria.get("unnecessary_investigations", [])
    
    # Map investigation IDs to human-readable names from case data
    case_investigations: Dict[str, str] = {}
    for inv in case_data.get("investigations", []):
        inv_id = str(inv.get("id", "")).lower()
        if inv_id:
            case_investigations[inv_id] = inv.get("name", inv_id.upper())
            
    # Map examination types to names
    case_examinations: Dict[str, str] = {}
    for ex in case_data.get("examinations", []):
        ex_type = str(ex.get("type", "")).lower()
        if ex_type:
            case_examinations[ex_type] = ex.get("name", ex_type.title() + " Examination")
    
    # ── 1. Evaluate History Taking (Max 20) ──────────────────────────────────
    asked_categories = set()
    for act in actions:
        if act.action_type == "question" and act.category:
            asked_categories.add(act.category.lower())
            
    if critical_categories:
        matched_critical = [c for c in critical_categories if c.lower() in asked_categories]
        history_score = (len(matched_critical) / len(critical_categories)) * 20.0
        
        if len(matched_critical) == len(critical_categories):
            strengths.append("Comprehensive clinical history taking; systematically gathered all key symptom characteristics and risk factors.")
        else:
            missed = [c for c in critical_categories if c.lower() not in asked_categories]
            missed_labels = [QUESTION_CATEGORY_DESCRIPTIONS.get(c, c.replace("_", " ")) for c in missed]
            weaknesses.append(f"Incomplete history taking; failed to inquire about: {', '.join(missed_labels)}.")
            for c in missed:
                desc = QUESTION_CATEGORY_DESCRIPTIONS.get(c, c.replace("_", " "))
                critical_mistakes.append(f"Failed to ask about {desc}.")
    else:
        history_score = 20.0

    # ── 2. Evaluate Physical Examination ────────────────────────────────────
    performed_exams = set()
    for act in actions:
        if act.action_type == "examination" and act.category:
            performed_exams.add(act.category.lower())
            
    if case_examinations:
        if len(performed_exams) == 0:
            critical_mistakes.append("Failed to perform any focused physical examination.")
            weaknesses.append("Omitted physical examination; missed vital objective clinical signs.")
        else:
            # Check key specialty-specific physical examinations
            spec_lower = (case_data.get("specialty", "") + " " + case_data.get("title", "") + " " + correct_diagnosis).lower()
            key_exam_types: List[str] = []
            if any(k in spec_lower for k in ["stroke", "neuro", "migraine", "headache", "weakness"]):
                key_exam_types.append("neurological")
            if any(k in spec_lower for k in ["appendic", "gastro", "gerd", "abdom"]):
                key_exam_types.append("abdominal")
            if any(k in spec_lower for k in ["asthma", "pulmon", "wheez", "breath", "broncho"]):
                key_exam_types.append("respiratory")
            if any(k in spec_lower for k in ["coronary", "cardio", "angina", "pericard", "chest pain", "heart"]):
                key_exam_types.append("cardiovascular")
            if any(k in spec_lower for k in ["pyelonephritis", "flank", "kidney", "urinary"]):
                key_exam_types.extend(["back", "abdominal"])
            if any(k in spec_lower for k in ["dvt", "thrombosis", "calf", "leg swelling"]):
                key_exam_types.extend(["extremity", "cardiovascular"])

            for ket in key_exam_types:
                if ket in case_examinations and ket not in performed_exams:
                    exam_name = case_examinations.get(ket, ket.title() + " Examination")
                    critical_mistakes.append(f"Failed to perform essential {exam_name}.")
                    weaknesses.append(f"Missed high-priority physical assessment ({exam_name}).")

    # ── 3. Evaluate Investigation Selection (Max 20) ────────────────────────
    ordered_investigations = set()
    for act in actions:
        if act.action_type == "investigation" and act.category:
            ordered_investigations.add(act.category.lower())
            
    if required_investigations:
        matched_investigations = [i for i in required_investigations if i.lower() in ordered_investigations]
        investigation_score = (len(matched_investigations) / len(required_investigations)) * 20.0
        
        if len(matched_investigations) == len(required_investigations):
            req_names = [case_investigations.get(i.lower(), i.upper()) for i in required_investigations]
            strengths.append(f"Appropriately ordered essential diagnostic investigations ({', '.join(req_names)}).")
        else:
            missed_inv = [i for i in required_investigations if i.lower() not in ordered_investigations]
            missed_names = [case_investigations.get(i.lower(), i.upper()) for i in missed_inv]
            weaknesses.append(f"Missed essential diagnostic tests: {', '.join(missed_names)}.")
            for i in missed_inv:
                test_name = case_investigations.get(i.lower(), i.upper())
                critical_mistakes.append(f"Failed to order essential investigation: {test_name}.")
    else:
        investigation_score = 20.0

    # ── 4. Evaluate Resource Efficiency (Max 5) ─────────────────────────────
    # Deduct 2.5 points for each unnecessary test ordered
    wasted_tests = [i for i in unnecessary_investigations if i.lower() in ordered_investigations]
    efficiency_score = max(0.0, 5.0 - (len(wasted_tests) * 2.5))
    
    if len(wasted_tests) > 0:
        wasted_names = [case_investigations.get(i.lower(), i.upper()) for i in wasted_tests]
        weaknesses.append(f"Ordered low-yield / unnecessary diagnostic testing ({', '.join(wasted_names)}).")
        for i in wasted_tests:
            test_name = case_investigations.get(i.lower(), i.upper())
            critical_mistakes.append(f"Incurred unnecessary cost and delay by ordering low-yield {test_name} prior to standard workup.")
    else:
        strengths.append("Excellent resource stewardship; avoided high-cost unnecessary investigations.")

    # ── 5. Evaluate Differential Diagnosis Updates (Max 15) ──────────────────
    update_count = sum(1 for act in actions if act.action_type == "diagnosis_update")
    if update_count >= 2:
        differential_score = 15.0
        strengths.append("Consistently updated differential diagnoses as new clinical data arrived.")
    elif update_count == 1:
        differential_score = 10.0
        weaknesses.append("Updated hypothesis only once; continuous reassessment is advised as evidence evolves.")
    else:
        differential_score = 0.0
        weaknesses.append("Did not record or update differential diagnoses during the clinical encounter.")
        critical_mistakes.append("Failed to formulate and maintain dynamic differential diagnoses during workup.")

    # ── 6. Evaluate Final Decision (Max 5) ──────────────────────────────────
    final_diag_str = (session.final_diagnosis or "").lower().strip()
    is_correct = False
    
    for subtype in correct_subtypes:
        if subtype.lower() in final_diag_str:
            is_correct = True
            break
            
    if not is_correct and correct_diagnosis:
        if correct_diagnosis.lower() in final_diag_str:
            is_correct = True
            
    target_name = correct_diagnosis or case_data.get("title", "the correct condition")
    if is_correct:
        decision_score = 5.0
        strengths.append(f"Correctly identified final diagnosis: {session.final_diagnosis}.")
    else:
        decision_score = 0.0
        submitted_label = session.final_diagnosis or "Incomplete"
        weaknesses.append(f"Incorrect final diagnosis. Submitted: '{submitted_label}', expected: '{target_name}'.")
        critical_mistakes.append(f"Incorrect final diagnosis: Submitted '{submitted_label}', but the correct clinical diagnosis was '{target_name}'.")

    # ── 7. Evaluate Referral / Triage Disposition (Additive Competency) ───────
    referral_criteria = criteria.get("referral_criteria", {})
    tier = getattr(session, "facility_tier", "tertiary") or "tertiary"
    tier_map = referral_criteria.get("correct_disposition_by_tier", {})
    correct_disposition = tier_map.get(tier, "manage_locally" if tier == "tertiary" else "refer")
    student_disposition = getattr(session, "disposition", None) or "manage_locally"
    
    if tier == "tertiary":
        # At tertiary hospital, all modalities are available; standard local management is accepted
        disposition_score = 5.0 if student_disposition in ["manage_locally", correct_disposition] else 2.5
    else:
        # At CHC or PHC, triage and referral thresholds are strictly evaluated
        disposition_score = 5.0 if student_disposition == correct_disposition else 0.0

    if tier != "tertiary":
        if student_disposition == correct_disposition:
            strengths.append(f"Correctly recognized the limits of this {tier.upper()} facility tier and executed safe disposition ('{student_disposition.replace('_', ' ')}').")
        else:
            weaknesses.append(f"Inappropriate facility disposition. Selected '{student_disposition.replace('_', ' ')}', but clinical guidelines indicate '{correct_disposition.replace('_', ' ')}' for {tier.upper()} tier.")
            if correct_disposition == "refer" and student_disposition == "manage_locally":
                critical_mistakes.append(f"Attempted to manage a case requiring referral at a {tier.upper()} facility without the resources to safely do so.")
            elif correct_disposition == "manage_locally" and student_disposition == "refer":
                weaknesses.append(f"Unnecessary referral from {tier.upper()} tier for a condition that can be safely managed locally.")

    scores = {
        "history_score": round(history_score, 1),
        "investigation_score": round(investigation_score, 1),
        "resource_efficiency_score": round(efficiency_score, 1),
        "differential_score": round(differential_score, 1),
        "decision_score": round(decision_score, 1),
        "disposition_score": round(disposition_score, 1),
    }

    return scores, strengths, weaknesses, critical_mistakes, disposition_score, student_disposition, correct_disposition
