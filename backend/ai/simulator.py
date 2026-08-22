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

def get_offline_patient_response(question: str, qa_pairs: List[Dict[str, Any]]) -> Tuple[str, str]:
    q_lower = question.lower()
    best_match = None
    best_score = 0
    best_category = "other"
    
    for qa in qa_pairs:
        score = 0
        for kw in qa.get("keywords", []):
            if kw in q_lower:
                score += 2 # Match keyword
        
        # Give bonus for specific categories
        if score > best_score:
            best_score = score
            best_match = qa.get("answer")
            best_category = qa.get("question_category", "other")
            
    if best_score > 0 and best_match:
        return best_match, best_category
    
    # Generic patient responses
    if "hello" in q_lower or "hi " in q_lower or q_lower == "hi":
        return "Hello doctor. Thank you for seeing me. I'm feeling really uncomfortable.", "other"
    if "help" in q_lower or "treat" in q_lower or "give" in q_lower:
        return "Please, doctor, do whatever you need to do to make this pressure go away.", "other"
        
    return "I'm not sure about that, doctor. I'm just really focused on this pressure in my chest and feeling a bit scared.", "other"

def simulate_patient(
    question: str,
    case_data: Dict[str, Any],
    chat_history: List[Dict[str, str]]
) -> Tuple[str, str]:
    """
    Simulates the patient's response. Falls back to offline matching if settings.DEMO_MODE is True
    or if AI generation fails.
    """
    qa_pairs = case_data.get("qa_pairs", [])
    
    # Check if we should use demo mode
    if settings.DEMO_MODE:
        return get_offline_patient_response(question, qa_pairs)
        
    try:
        # Load prompt template
        template = load_prompt_template("patient_simulator.txt")
        if not template:
            return get_offline_patient_response(question, qa_pairs)
            
        patient = case_data.get("patient", {})
        
        # Build facts text
        facts_list = []
        for qa in qa_pairs:
            facts_list.append(f"- {qa.get('fact')} -> Answer if asked: {qa.get('answer')}")
        facts_text = "\n".join(facts_list)
        
        # Build chat history text
        history_list = []
        for msg in chat_history[-10:]: # Keep last 10 messages for context
            role = "Student" if msg.get("role") == "student" else "Patient"
            history_list.append(f"{role}: {msg.get('text')}")
        history_text = "\n".join(history_list)
        
        # Format instructions
        system_prompt = template.format(
            patient_name=patient.get("name", "the patient"),
            patient_age=patient.get("age", 52),
            patient_sex=patient.get("sex", "Male"),
            chief_complaint=patient.get("chief_complaint", "Chest discomfort"),
            case_facts=facts_text,
            chat_history="",
            latest_question=""
        )
        
        # Call AI
        answer = ai_client.generate_text(
            system_prompt=system_prompt,
            prompt=f"Student Chat History:\n{history_text}\n\nStudent's latest question: {question}\n\nPatient Response:"
        )
        
        # Determine category offline (for simpler categorization)
        _, category = get_offline_patient_response(question, qa_pairs)
        return answer.strip(), category
        
    except Exception as e:
        print(f"simulate_patient AI error: {e}. Falling back to offline matching.")
        return get_offline_patient_response(question, qa_pairs)
