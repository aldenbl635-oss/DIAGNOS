import os
from typing import List, Dict, Any, Tuple
from ai.client import ai_client
from config import settings


def load_prompt_template(filename: str) -> str:
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(current_dir, "prompts", filename)
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def get_offline_patient_response(
    question: str,
    qa_pairs: List[Dict[str, Any]],
    case_data: Dict[str, Any] = None,
) -> Tuple[str, str]:
    """
    Keyword-match against a case's qa_pairs, or return a CASE-AWARE fallback.
    Never returns a chest-specific response for non-cardiac cases.
    """
    q_lower = question.lower()
    best_match = None
    best_score = 0
    best_category = "other"

    for qa in (qa_pairs or []):
        score = 0
        for kw in qa.get("keywords", []):
            if kw in q_lower:
                score += 2
        if score > best_score:
            best_score = score
            best_match = qa.get("answer")
            best_category = qa.get("question_category", "other")

    if best_score > 0 and best_match:
        return best_match, best_category

    # Case-aware fallbacks — derive chief complaint from case data
    complaint = "my condition"
    if case_data:
        patient = case_data.get("patient", {})
        complaint = (
            patient.get("chief_complaint")
            or case_data.get("presentation", {}).get("chief_complaint")
            or complaint
        )

    if "hello" in q_lower or ("hi" in q_lower.split()) or q_lower == "hi":
        return f"Hello doctor. Thank you for seeing me. I'm not feeling well.", "other"
    if "help" in q_lower or "treat" in q_lower:
        return f"Please, doctor, do whatever you need to help me with this {complaint}.", "other"

    return (
        f"I'm not sure about that, doctor. I'm really focused on this {complaint} right now.",
        "other",
    )


def simulate_patient(
    question: str,
    case_data: Dict[str, Any],
    chat_history: List[Dict[str, str]],
) -> Tuple[str, str]:
    """
    Simulates the patient's response.
    Falls back to offline matching if settings.DEMO_MODE is True or if AI generation fails.
    """
    qa_pairs = case_data.get("qa_pairs", [])

    if settings.DEMO_MODE:
        return get_offline_patient_response(question, qa_pairs, case_data)

    try:
        template = load_prompt_template("patient_simulator.txt")
        if not template:
            return get_offline_patient_response(question, qa_pairs, case_data)

        patient = case_data.get("patient", {})
        chief_complaint = (
            patient.get("chief_complaint")
            or case_data.get("presentation", {}).get("chief_complaint", "my condition")
        )

        facts_list = [
            f"- {qa.get('fact')} -> Answer if asked: {qa.get('answer')}"
            for qa in qa_pairs
        ]
        facts_text = "\n".join(facts_list)

        history_list = []
        for msg in chat_history[-10:]:
            role = "Student" if msg.get("role") == "student" else "Patient"
            history_list.append(f"{role}: {msg.get('text')}")
        history_text = "\n".join(history_list)

        system_prompt = template.format(
            patient_name=patient.get("name", "the patient"),
            patient_age=patient.get("age", 52),
            patient_sex=patient.get("sex", "Unknown"),
            chief_complaint=chief_complaint,
            case_facts=facts_text,
            chat_history="",
            latest_question="",
        )

        answer = ai_client.generate_text(
            system_prompt=system_prompt,
            prompt=(
                f"Student Chat History:\n{history_text}\n\n"
                f"Student's latest question: {question}\n\nPatient Response:"
            ),
        )

        _, category = get_offline_patient_response(question, qa_pairs, case_data)
        return answer.strip(), category

    except Exception as e:
        print(f"simulate_patient AI error: {e}. Falling back to offline matching.")
        return get_offline_patient_response(question, qa_pairs, case_data)
