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
    # Formulate a deterministic mock evaluation
    has_ecg = False
    has_troponin = False
    ordered_ct = False
    ecg_index = 999
    troponin_index = 999
    ct_index = 999
    
    for i, act in enumerate(actions):
        if act.action_type == "investigation":
            name = act.content.lower()
            if "ecg" in name or "electrocardiogram" in name:
                has_ecg = True
                ecg_index = i
            elif "troponin" in name:
                has_troponin = True
                troponin_index = i
            elif "ct" in name:
                ordered_ct = True
                ct_index = i
                
    # Base scores out of 10
    reasoning_base = 8.5
    interpretation_base = 8.0
    
    # Sequence checks
    if has_ecg and has_troponin:
        if ecg_index < troponin_index:
            reasoning_base += 1.0 # Good diagnostic flow
        else:
            reasoning_base -= 1.0 # Troponin ordered before ECG
    else:
        reasoning_base -= 3.0
        
    if ordered_ct:
        if ct_index < ecg_index or ct_index < troponin_index:
            reasoning_base -= 2.5 # CT ordered too early
            interpretation_base -= 2.0
            
    # Justification text evaluation
    justification = (session.evidence_justification or "").lower()
    justification_keywords = ["elevation", "stemi", "st-segment", "troponin", "inferior", "leads", "ecg", "ischemia"]
    matched_justification = [kw for kw in justification_keywords if kw in justification]
    
    interpretation_base += len(matched_justification) * 0.3
    
    # Cap between 1.0 and 10.0
    reasoning_base = max(1.0, min(10.0, reasoning_base))
    interpretation_base = max(1.0, min(10.0, interpretation_base))
    
    summary = (
        f"The student demonstrated a reasonable diagnostic workup. "
        f"The final diagnosis of {session.final_diagnosis} was medically sound. "
    )
    if ordered_ct:
        summary += "However, ordering a chest CT scan early on represented significant resource waste."
    else:
        summary += "The sequence of testing (ECG followed by Troponins) was highly efficient and aligned with clinical guidelines."
        
    return {
        "reasoning_score": round(reasoning_base, 1),
        "evidence_interpretation_score": round(interpretation_base, 1),
        "decision_score": 9.0 if (session.final_diagnosis and "coronary" in session.final_diagnosis.lower()) else 4.0,
        "strengths": ["Logical prioritization of initial cardiac tests."],
        "weaknesses": ["Consider explaining the specific leads involved in the ECG findings in your documentation." if not "lead" in justification else "No major weaknesses in baseline interpretation."],
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
    
    # 4. Merge lists
    merged_strengths = list(set(rule_strengths + ai_eval_result.get("strengths", [])))
    merged_weaknesses = list(set(rule_weaknesses + ai_eval_result.get("weaknesses", [])))
    merged_critical = list(set(rule_critical + ai_eval_result.get("critical_mistakes", [])))
    
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
        final_score=round(final_score, 1),
        strengths=merged_strengths,
        weaknesses=merged_weaknesses,
        critical_mistakes=merged_critical,
        summary=ai_eval_result.get("overall_reasoning_summary", "Evaluation complete.")
    )
    
    return evaluation
