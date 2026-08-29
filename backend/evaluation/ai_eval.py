import json
import os
from typing import List, Dict, Any
from ai.client import ai_client
from evaluation.scorer import evaluate_session_rules
import models
from config import settings

def load_prompt_template(filename: str) -> str:
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(current_dir, "prompts", filename)
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def get_offline_ai_eval(
    session: models.SimulationSession,
    case_data: Dict[str, Any],
    actions: List[models.StudentAction]
) -> Dict[str, Any]:
    criteria = case_data.get("evaluation_criteria", {})
    correct_diagnosis = criteria.get("correct_diagnosis", "")
    correct_subtypes = criteria.get("correct_subtypes", [])
    required_invs = [str(i).lower() for i in criteria.get("required_investigations", [])]
    unnecessary_invs = [str(i).lower() for i in criteria.get("unnecessary_investigations", [])]
    case_inv_map = {str(inv.get("id", "")).lower(): inv.get("name", inv.get("id")) for inv in case_data.get("investigations", [])}
    patient_name = case_data.get("patient", {}).get("name", "the patient")

    ordered_invs = []
    has_unnecessary = False
    first_exam_idx = 999
    first_inv_idx = 999

    for i, act in enumerate(actions):
        if act.action_type == "examination" and first_exam_idx == 999:
            first_exam_idx = i
        elif act.action_type == "investigation":
            if first_inv_idx == 999:
                first_inv_idx = i
            inv_cat = str(act.category or "").lower()
            ordered_invs.append(inv_cat)
            if inv_cat in unnecessary_invs:
                has_unnecessary = True

    # Base scores out of 10
    reasoning_base = 8.5
    interpretation_base = 7.5

    # Sequence & testing checks
    if required_invs:
        missing_required = [r for r in required_invs if r not in ordered_invs]
        if not missing_required:
            reasoning_base += 1.0  # All essential tests ordered
        else:
            reasoning_base -= min(4.0, len(missing_required) * 2.0)

    if has_unnecessary:
        reasoning_base -= 2.0
        interpretation_base -= 1.5

    if first_exam_idx < first_inv_idx:
        reasoning_base += 0.5  # Performed physical exam before tests

    # Case-specific justification text evaluation
    justification = (session.evidence_justification or "").lower()
    keywords = set()
    for word in (correct_diagnosis or "").replace("-", " ").split():
        if len(word) > 3:
            keywords.add(word.lower())
    for sub in correct_subtypes:
        for word in sub.replace("-", " ").split():
            if len(word) > 3:
                keywords.add(word.lower())
    for inv in case_data.get("investigations", []):
        if str(inv.get("id", "")).lower() in required_invs:
            for word in inv.get("interpretation", "").replace(",", " ").replace(".", " ").split():
                if len(word) > 4:
                    keywords.add(word.lower())

    matched_keywords = [kw for kw in keywords if kw in justification]
    interpretation_base += min(2.5, len(matched_keywords) * 0.4)

    # Diagnostic accuracy check
    final_diag_str = (session.final_diagnosis or "").lower().strip()
    is_correct = False
    for subtype in correct_subtypes:
        if subtype.lower() in final_diag_str:
            is_correct = True
            break
    if not is_correct and correct_diagnosis:
        if correct_diagnosis.lower() in final_diag_str:
            is_correct = True

    reasoning_base = max(1.0, min(10.0, reasoning_base))
    interpretation_base = max(1.0, min(10.0, interpretation_base))
    decision_score = 9.5 if is_correct else 3.5

    # Dynamic summary
    if is_correct:
        summary = f"The student demonstrated structured diagnostic reasoning for {patient_name}. The final diagnosis of '{session.final_diagnosis}' was clinically accurate and supported by evidence."
    else:
        summary = f"The student evaluated {patient_name}, but the final diagnosis of '{session.final_diagnosis or 'Incomplete'}' did not match the expected clinical condition ({correct_diagnosis})."

    if has_unnecessary:
        summary += " Note that ordering low-yield diagnostic imaging prior to standard screening led to resource inefficiency."
    elif required_invs and all(r in ordered_invs for r in required_invs):
        summary += " Investigation selection was focused, efficient, and well-aligned with clinical guidelines."

    ai_strengths = []
    ai_weaknesses = []
    if is_correct:
        ai_strengths.append(f"Logical synthesis leading to accurate identification of {correct_diagnosis}.")
    if matched_keywords:
        ai_strengths.append("Evidence justification effectively cited key clinical findings and interpretations.")
    if has_unnecessary:
        ai_weaknesses.append("Avoid ordering advanced diagnostic imaging without primary clinical justification.")

    return {
        "reasoning_score": round(reasoning_base, 1),
        "evidence_interpretation_score": round(interpretation_base, 1),
        "decision_score": round(decision_score, 1),
        "strengths": ai_strengths,
        "weaknesses": ai_weaknesses,
        "critical_mistakes": [],
        "overall_reasoning_summary": summary
    }

def evaluate_clinical_reasoning(
    session: models.SimulationSession,
    case_data: Dict[str, Any],
    actions: List[models.StudentAction]
) -> models.Evaluation:
    # 1. Compute rule-based metrics
    rules_scores, rule_strengths, rule_weaknesses, rule_critical = evaluate_session_rules(session, case_data, actions)
    
    ai_eval_result = {}
    
    # 2. Get AI or offline qualitative grades
    if settings.DEMO_MODE:
        ai_eval_result = get_offline_ai_eval(session, case_data, actions)
    else:
        try:
            template = load_prompt_template("reasoning_evaluator.txt")
            
            # Format performance logs
            act_logs = []
            for act in actions:
                cost_str = f" (${act.cost})" if act.cost > 0 else ""
                category_str = f" [{act.category}]" if act.category else ""
                act_logs.append(f"- {act.timestamp.strftime('%H:%M:%S')} | {act.action_type}{category_str}: {act.content}{cost_str}")
            action_log_text = "\n".join(act_logs)
            
            diff_updates = []
            for act in actions:
                if act.action_type == "diagnosis_update":
                    diff_updates.append(f"- {act.timestamp.strftime('%H:%M:%S')}: {act.content}")
            diff_updates_text = "\n".join(diff_updates) if diff_updates else "None recorded."
            
            prompt_content = template.format(
                case_title=case_data.get("title"),
                correct_diagnosis=case_data.get("evaluation_criteria", {}).get("correct_diagnosis"),
                expected_pathway=", ".join(case_data.get("evaluation_criteria", {}).get("required_investigations", [])),
                action_log=action_log_text,
                differential_updates=diff_updates_text,
                student_final_diagnosis=session.final_diagnosis,
                student_priority=session.immediate_priority,
                student_justification=session.evidence_justification
            )
            
            system_instruction = "You are a clinical assessor. Return ONLY a valid JSON object matching the requested schema. No markdown formatting."
            
            # Call AI Client
            raw_response = ai_client.generate_text(
                system_prompt=system_instruction,
                prompt=prompt_content,
                json_mode=True
            )
            
            # Sanitize response just in case
            sanitized = raw_response.strip()
            if sanitized.startswith("```json"):
                sanitized = sanitized[7:]
            if sanitized.endswith("```"):
                sanitized = sanitized[:-3]
                
            ai_eval_result = json.loads(sanitized.strip())
            
        except Exception as e:
            print(f"evaluate_clinical_reasoning AI error: {e}. Falling back to offline grading.")
            ai_eval_result = get_offline_ai_eval(session, case_data, actions)
            
    # 3. Map qualitative/AI scores into final weights
    # Clinical Reasoning: max 15 (AI score out of 10 scaled by 1.5)
    # Evidence Interpretation: max 20 (AI score out of 10 scaled by 2.0)
    ai_reasoning_scaled = float(ai_eval_result.get("reasoning_score", 8.0)) * 1.5
    ai_interpretation_scaled = float(ai_eval_result.get("evidence_interpretation_score", 8.0)) * 2.0
    
    # Clip just in case
    ai_reasoning_scaled = max(0.0, min(15.0, ai_reasoning_scaled))
    ai_interpretation_scaled = max(0.0, min(20.0, ai_interpretation_scaled))
    
    # Sum it up
    # History Taking: 20
    # Differential Diagnosis: 15
    # Investigation Selection: 20
    # Evidence Interpretation: 20
    # Clinical Reasoning: 15
    # Resource Efficiency: 5
    # Final Decision: 5
    # Total: 100
    final_score = (
        rules_scores["history_score"] +                  # Max 20
        rules_scores["differential_score"] +             # Max 15
        rules_scores["investigation_score"] +            # Max 20
        ai_interpretation_scaled +                       # Max 20
        ai_reasoning_scaled +                            # Max 15
        rules_scores["resource_efficiency_score"] +      # Max 5
        rules_scores["decision_score"]                   # Max 5
    )
    
    # 4. Compute communication and patient interaction metrics
    emotional_events = []
    if session.patient_agent_state:
        if isinstance(session.patient_agent_state, str):
            try:
                state_dict = json.loads(session.patient_agent_state)
            except Exception:
                state_dict = {}
        else:
            state_dict = session.patient_agent_state
        emotional_events = state_dict.get("emotional_events", [])

    from ai.interaction_analyzer import InteractionAnalyzer
    analyzer = InteractionAnalyzer()
    
    comm_score = 100.0
    empathy = 50.0
    interaction = 75.0
    
    had_rude = False
    had_threat = False
    used_empathetic_after = False
    empathetic_count = 0
    reassuring_count = 0
    rude_count = 0
    threat_count = 0
    insult_count = 0
    dismissive_count = 0
    frightening_count = 0
    rushed_count = 0
    
    for act in actions:
        if act.action_type == "question":
            analysis = analyzer.analyze(act.content)
            intent = analysis.get("intent", "neutral")
            
            if analysis.get("threat") or intent == "threatening" or intent == "threat":
                had_threat = True
                threat_count += 1
                comm_score -= 40
                empathy -= 30
            elif analysis.get("insult") or intent == "insulting" or intent == "insult":
                had_rude = True
                insult_count += 1
                comm_score -= 30
                empathy -= 25
            elif analysis.get("tone") == "rude" or intent == "rude":
                had_rude = True
                rude_count += 1
                comm_score -= 20
                empathy -= 20
            elif analysis.get("dismissive") or intent == "dismissive":
                had_rude = True
                dismissive_count += 1
                comm_score -= 15
                empathy -= 15
            elif analysis.get("alarmist") or intent == "alarmist" or intent == "frightening":
                frightening_count += 1
                comm_score -= 15
                empathy -= 15
            elif intent == "rushed":
                rushed_count += 1
                comm_score -= 10
                empathy -= 5
            elif analysis.get("empathetic") or intent == "empathetic":
                empathetic_count += 1
                empathy += 15
                comm_score += 5
                if had_rude or had_threat:
                    used_empathetic_after = True
            elif analysis.get("reassurance") or intent == "reassuring":
                reassuring_count += 1
                empathy += 10
                comm_score += 5
                if had_rude or had_threat:
                    used_empathetic_after = True
            elif intent == "respectful" or intent == "neutral":
                empathy += 5
                comm_score += 3
    
    interaction = 100.0
    # Deduct for student-induced distress
    interaction -= threat_count * 30
    interaction -= insult_count * 20
    interaction -= rude_count * 15
    interaction -= dismissive_count * 15
    interaction -= frightening_count * 20
    interaction -= rushed_count * 10

    distressed_count = 0
    for e in emotional_events:
        lbl = e.get("emotion_label", "")
        if lbl in ["Shocked", "Angry"]:
            distressed_count += 1
            interaction -= 10
            
    if (had_rude or had_threat) and used_empathetic_after:
        interaction += 20
        comm_score += 15
    elif (had_rude or had_threat) and not used_empathetic_after:
        interaction -= 15
        
    comm_score = max(10.0, min(100.0, comm_score))
    empathy = max(0.0, min(100.0, empathy))
    interaction = max(10.0, min(100.0, interaction))
    
    comm_strengths = []
    comm_weaknesses = []
    comm_critical = []
    
    if empathetic_count >= 2 or reassuring_count >= 2:
        comm_strengths.append("Demonstrated outstanding empathy and active reassurance.")
    if not had_rude and not had_threat and comm_score >= 85:
        comm_strengths.append("Maintained excellent professionalism throughout the encounter.")
    if (had_rude or had_threat) and used_empathetic_after:
        comm_strengths.append("Successfully repaired the therapeutic relationship after a communication breakdown.")
        
    if had_threat:
        comm_critical.append("Threatening or unprofessional clinical tone used during the encounter.")
    if frightening_count > 0:
        comm_weaknesses.append(f"Used alarmist language {frightening_count} time(s), causing patient distress.")
    if rude_count or insult_count:
        comm_weaknesses.append("Rude or hostile tone used which damaged patient trust.")
    if distressed_count > 0:
        comm_weaknesses.append(f"Patient experienced significant emotional distress ({distressed_count} instances).")
    if (had_rude or had_threat) and not used_empathetic_after:
        comm_weaknesses.append("Failed to acknowledge or apologize for a rude/insensitive comment.")

    # Merge lists
    merged_strengths = list(set(rule_strengths + ai_eval_result.get("strengths", []) + comm_strengths))
    merged_weaknesses = list(set(rule_weaknesses + ai_eval_result.get("weaknesses", []) + comm_weaknesses))
    merged_critical = list(set(rule_critical + ai_eval_result.get("critical_mistakes", []) + comm_critical))
    
    # Construct Evaluation model
    evaluation = models.Evaluation(
        session_id=session.id,
        history_score=rules_scores["history_score"],
        differential_score=rules_scores["differential_score"],
        investigation_score=rules_scores["investigation_score"],
        evidence_interpretation_score=round(ai_interpretation_scaled, 1),
        reasoning_score=round(ai_reasoning_scaled, 1),
        decision_score=rules_scores["decision_score"],
        resource_efficiency_score=rules_scores["resource_efficiency_score"],
        communication_score=round(comm_score, 1),
        empathy_score=round(empathy, 1),
        patient_interaction_score=round(interaction, 1),
        emotional_timeline=emotional_events,
        final_score=round(final_score, 1),
        strengths=merged_strengths,
        weaknesses=merged_weaknesses,
        critical_mistakes=merged_critical,
        summary=ai_eval_result.get("overall_reasoning_summary", "Evaluation complete.")
    )
    
    return evaluation
