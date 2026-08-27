"""
Patient Agent — main orchestrator for the AI virtual patient.
This is the central service that replaces the old simulate_patient() function.

Architecture:
  PatientAgent.generate_response()
    → Loads patient state
    → Builds LLM prompt with clinical facts + emotional state + memory
    → Calls LLM (or demo engine fallback)
    → Parses structured JSON output
    → Updates emotional state, memory, beliefs
    → Returns sanitized response (no hidden clinical data exposed)
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple

from ai.client import ai_client
from ai.patient_state import PatientAgentState
from ai.patient_emotion import EmotionalState
from ai.patient_memory import PatientMemory
from ai.patient_personality import PersonalityProfile
from ai.patient_reasoning import (
    classify_student_communication,
    parse_agent_response,
    compute_emotion_delta_from_style,
    detect_existential_threat,
    compute_existential_threat_emotion_spike,
)
from config import settings


def _load_prompt(filename: str) -> str:
    """Load a prompt template from the ai/prompts/ directory."""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "prompts", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def fetch_realtime_definition(query: str) -> Optional[str]:
    import requests
    try:
        url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json"
        res = requests.get(url, timeout=5)
        if res.status_code in [200, 202]:
            data = res.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                return abstract
            related = data.get("RelatedTopics", [])
            for item in related:
                if isinstance(item, dict) and "Text" in item and len(item["Text"]) > 20:
                    return item["Text"]
    except Exception as e:
        print(f"Error fetching real-time data: {e}")
    return None


def _build_clinical_facts_text(case_data: Dict[str, Any]) -> str:
    """Convert structured clinical_facts from case JSON into prompt text."""
    facts = case_data.get("clinical_facts", {})
    if not facts:
        # Legacy fallback: convert qa_pairs facts
        qa_pairs = case_data.get("qa_pairs", [])
        if qa_pairs:
            lines = [f"- {qa.get('fact', '')}" for qa in qa_pairs if qa.get("fact")]
            return "\n".join(lines)
        return "No clinical facts provided."

    lines = []

    def add_section(title: str, data: Any):
        if not data:
            return
        lines.append(f"\n[{title}]")
        if isinstance(data, list):
            for item in data:
                lines.append(f"  • {item}")
        elif isinstance(data, dict):
            for k, v in data.items():
                lines.append(f"  • {k.replace('_', ' ').title()}: {v}")
        else:
            lines.append(f"  {data}")

    add_section("Chief Complaint & Symptoms", facts.get("symptoms"))
    add_section("History of Presenting Illness", facts.get("history_of_illness"))
    add_section("Past Medical History", facts.get("past_medical_history"))
    add_section("Medications", facts.get("medications"))
    add_section("Allergies", facts.get("allergies"))
    add_section("Family History", facts.get("family_history"))
    add_section("Social & Lifestyle History", facts.get("social_history"))
    add_section("Review of Systems", facts.get("review_of_systems"))
    add_section("Physical Examination Findings (if examined)", facts.get("examination_findings"))
    add_section("Investigation Results (if ordered)", facts.get("investigation_results"))

    return "\n".join(lines) if lines else "No clinical facts provided."


def _build_conversation_text(conversation_history: List[Dict[str, str]], max_turns: int = 12) -> str:
    """Format recent conversation history for the prompt."""
    if not conversation_history:
        return "No prior conversation."
    recent = conversation_history[-max_turns:]
    lines = []
    for msg in recent:
        role = "Student" if msg.get("role") == "student" else "Patient (you)"
        lines.append(f"{role}: {msg.get('text', '')}")
    return "\n".join(lines)


class PatientAgent:
    """
    The AI Virtual Patient Agent.
    Generates contextually appropriate, emotionally reactive, memory-aware
    patient responses based on the student's input.
    """

    def __init__(self, case_data: Dict[str, Any]):
        self.case_data = case_data
        self.patient = case_data.get("patient", {})
        self.system_prompt_template = _load_prompt("patient_system.txt")
        self.clinical_facts_text = _build_clinical_facts_text(case_data)

    def _build_system_prompt(self, state: PatientAgentState) -> str:
        """Construct the full system prompt for this turn."""
        patient = self.patient
        name = patient.get("name", "the patient")

        # Convert personality to narrative description
        personality_narrative = state.personality.to_narrative()

        # Beliefs
        beliefs_text = "\n".join(
            f"- {b}" for b in state.beliefs
        ) if state.beliefs else "You have not formed any specific beliefs yet."

        # Goals
        goals_text = "\n".join(
            f"- {g}" for g in state.goals
        ) if state.goals else "Your main goal is to understand what is happening."

        # Emotional state description
        emotional_desc = state.emotion.to_prompt_description()

        # Memory summary
        memory_summary = state.memory.get_relevant_summary()

        return self.system_prompt_template.format(
            patient_name=name,
            patient_age=patient.get("age", "unknown"),
            patient_sex=patient.get("sex", "unknown"),
            patient_occupation=patient.get("occupation", "unknown"),
            chief_complaint=patient.get("chief_complaint", "discomfort"),
            clinical_facts=self.clinical_facts_text,
            personality_narrative=personality_narrative,
            patient_beliefs=beliefs_text,
            patient_goals=goals_text,
            emotional_state_description=emotional_desc,
            memory_summary=memory_summary,
            simulation_phase=state.simulation_phase,
        )

    def generate_response(
        self,
        state: PatientAgentState,
        conversation_history: List[Dict[str, str]],
        student_message: str,
        event_context: Optional[str] = None,  # e.g. "ECG just ordered"
    ) -> Tuple[PatientAgentState, Dict[str, Any]]:
        """
        Generate the patient's response and update state.

        Returns:
            (updated_state, response_dict)

        response_dict contains:
            response: str — patient's spoken text
            emotion_label: str — human-readable emotion state
            emotional_cue: str — brief behavioral description
            student_communication_classification: str
            communication_state: str
        """
        # Communication analysis layer
        from ai.patient_reasoning import analyze_student_communication_rule_based
        com_analysis = analyze_student_communication_rule_based(student_message)
        student_style = com_analysis["intent"]
        
        is_existential_threat = detect_existential_threat(student_message)

        # If an existential threat is detected, pre-spike the emotional state
        # so the LLM always builds its response from the correct emotional baseline.
        if is_existential_threat:
            spike = compute_existential_threat_emotion_spike(
                fear_of_death=state.personality.fear_of_death,
                emotional_sensitivity=state.personality.emotional_sensitivity,
            )
            # Apply spike directly onto the existing emotion object (in-place)
            state.emotion.set_values({k: v for k, v in spike.items() if v > 0})
            if spike.get("trust", 0) < 0:
                state.emotion.apply_update({"trust": spike["trust"]})

        # Determine the effective prompt message
        effective_message = student_message
        if event_context:
            effective_message = f"[System event: {event_context}]\n\nStudent says: {student_message}"

        if settings.DEMO_MODE:
            result = self._demo_response(state, student_message, student_style, conversation_history)
        else:
            try:
                result = self._llm_response(state, conversation_history, effective_message, student_style)
            except Exception as e:
                print(f"PatientAgent LLM error: {e}. Falling back to demo engine.")
                result = self._demo_response(state, student_message, student_style, conversation_history)

        # Apply updates to state
        updated_state = self._apply_result_to_state(state, result, student_style)

        # Map to lowercase communication state for UI bubble
        label = updated_state.emotion.get_label()
        mapping = {
            "Shocked": "shocked",
            "Frightened": "frightened",
            "Distressed": "devastated",
            "Anxious": "guarded",
            "Concerned": "concerned",
            "Reassured": "reassured",
            "Angry": "angry",
            "Confused": "confused",
            "Calm": "calm"
        }
        com_state = mapping.get(label, "calm")

        # Internally produce structured information (Section 23)
        internal_structured_info = {
            "patient_response": result.get("response", ""),
            "communication_analysis": {
                "intent": com_analysis["intent"],
                "tone": com_analysis["tone"],
                "severity": com_analysis["severity"],
                "contains_insult": com_analysis["contains_insult"],
                "contains_threat": com_analysis["contains_threat"],
                "empathetic": com_analysis["empathetic"],
                "reassuring": com_analysis["reassuring"],
                "patient_relevant": com_analysis["patient_relevant"]
            },
            "emotional_update": result.get("emotion_update", {}),
            "behavior": updated_state.emotion.get_behavioral_cue(),
            "memory_event": result.get("memory_event", {}).get("event") if result.get("memory_event") else None,
            "patient_state": label.lower()
        }
        print("\n=== INTERNAL AGENT STRUCTURED OUTPUT ===")
        print(json.dumps(internal_structured_info, indent=2))
        print("=========================================\n")

        # Build sanitized output for the route
        output = {
            "response": result.get("response", ""),
            "emotion_label": updated_state.emotion.get_label(),
            "emotional_cue": updated_state.emotion.get_behavioral_cue(),
            "student_communication_classification": student_style,
            "communication_state": com_state,
            "revealed_information": result.get("revealed_information", []),
        }

        return updated_state, output

    def _llm_response(
        self,
        state: PatientAgentState,
        conversation_history: List[Dict[str, str]],
        student_message: str,
        student_style: str,
    ) -> Dict[str, Any]:
        """Call the LLM and parse structured JSON response."""
        system_prompt = self._build_system_prompt(state)
        conversation_text = _build_conversation_text(conversation_history)

        user_prompt = (
            f"Recent conversation:\n{conversation_text}\n\n"
            f"Student's latest message: {student_message}\n\n"
            f"Respond as {self.patient.get('name', 'the patient')}. "
            f"Return ONLY valid JSON matching the specified schema."
        )

        raw = ai_client.generate_text(
            system_prompt=system_prompt,
            prompt=user_prompt,
            json_mode=True,
        )

        fallback_text = self._get_fallback_text(student_style)
        parsed = parse_agent_response(raw, fallback_text)

        # Override the student_communication_classification with our own classifier
        # (more reliable than asking the LLM to classify itself)
        parsed["student_communication_classification"] = student_style

        return parsed

    def _demo_response(
        self,
        state: PatientAgentState,
        student_message: str,
        student_style: str,
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Deterministic fallback response engine for DEMO_MODE.
        Respects personality, emotion, memory, and student communication style.
        """
        from ai.patient_reasoning import analyze_student_communication_rule_based
        com_analysis = analyze_student_communication_rule_based(student_message)
        intent = com_analysis["intent"]
        
        msg_lower = student_message.lower()
        patient_name = self.patient.get("name", "the patient")
        facts = self.case_data.get("clinical_facts", {})

        response_text = ""
        revealed = []
        memory_category = "question_answered"
        memory_importance = 0.5
        
        # Check if the patient has memory of recent insults/threats (within last 3 events)
        was_insulted = any(
            "hostile" in ev.get("description", "").lower() or 
            "insult" in ev.get("description", "").lower() or 
            "rude" in ev.get("description", "").lower() 
            for ev in state.emotional_events[-3:]
        )
        was_threatened = any(
            "threat" in ev.get("description", "").lower() 
            for ev in state.emotional_events[-3:]
        )
        
        # Determine emotion updates first
        emotion_delta = compute_emotion_delta_from_style(intent, state.personality.emotional_sensitivity)

        # 1. Handle Active Hostile Communication
        if intent == "threatening":
            response_text = "What?! Please don't threaten me. I'm just here because I'm sick. Please, don't say that."
            memory_category = "emotional"
            memory_importance = 0.95
        elif intent == "insulting":
            response_text = "There is no need to speak to me that way... I am just scared."
            memory_category = "emotional"
            memory_importance = 0.9
        elif intent == "rude":
            response_text = "Please, I'm trying to cooperate, but you're being very short with me. I just want some help."
            memory_category = "emotional"
            memory_importance = 0.7
        elif intent == "dismissive":
            response_text = "I feel like you aren't even listening to me. I'm really worried about my chest."
            memory_category = "clinical"
            memory_importance = 0.6

        # 2. Reassurance / Apology Repair
        elif any(w in msg_lower for w in ["sorry", "apologize", "didn't mean", "shouldn't have said"]) and (was_insulted or was_threatened or state.emotion.get_label() in ["Frightened", "Distressed"]):
            response_text = (
                "It's... okay. I just got really scared and upset. "
                "Please just tell me what's going on. I need to know."
            )
            # Repair emotion delta
            emotion_delta = {"fear": -25, "anxiety": -25, "trust": 30, "anger": -25, "shock": -30, "distress": -20}
            memory_category = "emotional"
            memory_importance = 0.8

        elif any(w in msg_lower for w in ["calm", "relax", "don't worry", "everything will be", "good hands", "take care of you", "deep breath"]):
            response_text = "Thank you, doctor. I'm trying to take deep breaths and calm down... it's just this heavy pressure."
            emotion_delta = {"fear": -20, "anxiety": -25, "trust": 20, "anger": -15, "shock": -25, "distress": -15}
            memory_category = "emotional"
            memory_importance = 0.7

        # 3. Existential Threat Intercept
        elif detect_existential_threat(student_message) or "gonna die" in msg_lower or "will die" in msg_lower or "going to die" in msg_lower or "you are dying" in msg_lower or "last wishes" in msg_lower:
            fear_of_death = state.personality.fear_of_death
            if fear_of_death > 70:
                response_text = (
                    "What?! No — please, you can't be saying that. My father died of a heart attack — "
                    "I can't... I have children. Please, tell me what's happening. Is there something you can do?"
                )
            else:
                response_text = "Wait, you think I might pass away? Is it that serious? Please, tell me what is happening. I need to know!"
            
            spike = compute_existential_threat_emotion_spike(
                fear_of_death=state.personality.fear_of_death,
                emotional_sensitivity=state.personality.emotional_sensitivity,
            )
            emotion_delta.update(spike)
            memory_category = "clinical"
            memory_importance = 0.95

        # 4. Patient Guarded / Uncooperative if trust is low and message is not empathetic
        elif state.emotion.trust < 30 and intent not in ["empathetic", "reassuring"]:
            response_text = "Why do you need to know that? You haven't explained anything, and I don't feel like you care about what is happening to me."
            memory_category = "emotional"
            memory_importance = 0.6

        # 5. Standard Case Q&A (Clinical facts)
        else:
            # Rebuild preface if patient recently insulted/threatened
            preface = ""
            if was_threatened:
                preface = "I'm still really shaken up by what you said... but if you must know, "
            elif was_insulted:
                preface = "I'm still hurt by how you spoke to me, but... "

            # Grab active case data clinical components
            facts = self.case_data.get("clinical_facts", {})
            symptoms = facts.get("symptoms", [])
            pmh = facts.get("past_medical_history", [])
            meds = facts.get("medications", [])
            allergies = facts.get("allergies", [])
            family_h = facts.get("family_history", [])
            social_h = facts.get("social_history", [])
            history_illness = facts.get("history_of_illness", [])

            # Check if this is an investigation event
            if "investigation ordered" in msg_lower or any(w in msg_lower for w in ["ordered", "order"]):
                chief_complaint = self.case_data.get("patient", {}).get("chief_complaint", "pain")
                if "chest" in chief_complaint.lower() or "heart" in chief_complaint.lower():
                    if state.emotion.anxiety > 50:
                        response_text = preface + "Is... is that machine for me? Is something wrong with my heart?"
                    else:
                        response_text = preface + "What does this test show? Should I be worried?"
                else:
                    if state.emotion.anxiety > 50:
                        response_text = preface + f"Is... is this test because of my {chief_complaint.lower()}?"
                    else:
                        response_text = preface + "What does this test show? Should I be worried?"
                memory_category = "clinical"
                memory_importance = 0.7

            # Memory check — already answered?
            elif state.memory.has_answered("smoking") and any(w in msg_lower for w in ["smok", "cigarette", "tobacco"]):
                smoke_fact = next((f for f in social_h if any(k in f.lower() for k in ["smoke", "cigarette", "tobacco", "smoker", "pack"])), "No, I don't smoke.")
                response_text = preface + f"Like I said, {smoke_fact}"
                memory_importance = 0.3

            elif state.memory.has_answered("diabetes") and any(w in msg_lower for w in ["diabet", "sugar", "glucose"]):
                diab_fact = next((f for f in pmh if any(k in f.lower() for k in ["diabet", "sugar", "glucose", "insulin"])), "No, I don't have diabetes.")
                response_text = preface + f"I already mentioned that: {diab_fact}"
                memory_importance = 0.3

            elif state.memory.has_answered("pain_location") and any(w in msg_lower for w in ["where", "location", "center"]):
                chief_complaint = self.case_data.get("patient", {}).get("chief_complaint", "pain")
                response_text = preface + f"I told you — it's primarily {chief_complaint.lower()}."
                memory_importance = 0.3

            # 1. Hello / Introduce / Name / Identity
            elif any(w in msg_lower for w in ["hello", "hi ", "good morning", "good afternoon", "introduce", "i am", "i'm dr", "my name", "what is your name", "who are you"]):
                p_name = self.case_data.get("patient", {}).get("name", "patient")
                init_stmt = self.case_data.get("patient", {}).get("initial_statement", "I'm not feeling well.")
                response_text = f"Hello doctor. I'm {p_name}. {init_stmt}"
                memory_category = "general"

            # 2. Onset / Trigger / Start / When
            elif any(w in msg_lower for w in ["when", "onset", "start", "happen", "begin", "trigger", "doing", "exert", "stairs", "walk", "climb", "run", "exercise"]):
                onset_fact = next((s for s in symptoms + history_illness if any(k in s.lower() for k in ["onset", "start", "trigger", "doing", "was ", "when", "exert", "began", "stairs", "walk", "climb", "morning", "afternoon", "sudden", "gradual"])), None)
                if onset_fact:
                    response_text = preface + f"It happened like this: {onset_fact}"
                else:
                    response_text = preface + f"It started recently."
                revealed = ["pain_characteristics"]
                state.memory.add_event("pain_onset", 0.8, "question_answered")

            # 3. Duration / How long
            elif any(w in msg_lower for w in ["how long", "duration", "since", "time", "minutes", "hours", "days", "weeks"]):
                dur_fact = next((s for s in symptoms + history_illness if any(k in s.lower() for k in ["hour", "minute", "day", "since", "duration", "long", "ago"])), None)
                if dur_fact:
                    response_text = preface + f"Well, {dur_fact}"
                else:
                    response_text = preface + "It has been going on for a little while now, it feels constant."
                revealed = ["pain_characteristics"]
                state.memory.add_event("pain_duration", 0.7, "question_answered")

            # 4. Age / Sex / Gender
            elif any(w in msg_lower for w in ["how old", "your age", "what is your age", "birthdate", "dob", "gender", "are you male", "are you female", "sex"]):
                p_age = self.case_data.get("patient", {}).get("age", "some")
                p_sex = self.case_data.get("patient", {}).get("sex", "patient")
                response_text = preface + f"I'm {p_age} years old, {p_sex}."
                revealed = ["past_medical_history"]

            # 5. Chief Complaint / Why here
            elif any(w in msg_lower for w in ["chief complaint", "what brought you", "why are you here", "what's wrong", "what is wrong", "what's the problem", "what is the problem", "how can i help", "why did you come"]):
                chief_complaint = self.case_data.get("patient", {}).get("chief_complaint", "pain")
                response_text = preface + f"I came in because of my {chief_complaint.lower()}."
                revealed = ["pain_characteristics"]

            # 6. Site / Location / Does it hurt / Pain / Symptoms description
            elif any(w in msg_lower for w in ["where", "location", "site", "side", "hurt", "hurts", "pain", "pains", "ache", "aching", "discomfort", "describe", "what kind", "type", "character", "sharp", "dull", "feel", "feeling", "feels"]) and "free" not in msg_lower:
                desc_symptom = symptoms[0] if symptoms else "pain and discomfort"
                chief_complaint = self.case_data.get("patient", {}).get("chief_complaint", "uncomfortable feeling")
                response_text = (
                    preface + f"It's primarily {chief_complaint.lower()}. "
                    f"To describe it: {desc_symptom}."
                )
                revealed = ["pain_characteristics"]
                state.memory.add_event("pain_location", 0.8, "question_answered")

            # 7. Radiation / Movement
            elif any(w in msg_lower for w in ["radiat", "spread", "go anywhere", "move", "travel", "shoot", "arm", "jaw", "shoulder", "neck", "back", "groin", "thigh", "leg"]):
                rad_symptom = next((s for s in symptoms if any(k in s.lower() for k in ["radiat", "spread", "travel", "extend", "move", "shift", "shoulder", "arm", "jaw", "neck", "back", "groin"])), None)
                if rad_symptom:
                    response_text = preface + f"Yes: {rad_symptom}"
                else:
                    response_text = preface + "No, the pain doesn't seem to go anywhere else, it's just local."
                revealed = ["pain_characteristics"]
                state.memory.add_event("pain_radiates", 0.9, "question_answered")
                memory_importance = 0.9

            # 8. Severity
            elif any(w in msg_lower for w in ["severity", "how bad", "scale of", "out of 10", "rate the pain", "how severe"]):
                severity_words = [s.lower() for s in symptoms]
                is_severe = any("severe" in s or "crushing" in s or "unbearable" in s for s in severity_words)
                if is_severe:
                    response_text = preface + "It's really bad, I'd say an 8 or 9 out of 10. It hurts quite intensely."
                else:
                    response_text = preface + "It's around a 6 or 7 out of 10. It's a very noticeable throbbing discomfort."
                revealed = ["pain_characteristics"]

            # 9. Exacerbating / Relieving factors
            elif any(w in msg_lower for w in ["better", "worse", "reliev", "ease", "improv", "aggravat", "nitroglycerin", "rest", "position", "deep breath", "breathing"]):
                better_worse_fact = next((s for s in symptoms + history_illness if any(k in s.lower() for k in ["better", "worse", "reliev", "ease", "position", "rest", "nitroglycerin", "breath", "constant"])), None)
                if better_worse_fact:
                    response_text = preface + f"Regarding that aspect: {better_worse_fact}."
                else:
                    response_text = preface + "It doesn't seem to change with deep breaths, positioning, or anything else. It's just constant."
                revealed = ["pain_characteristics"]

            # 10. Associated symptoms
            elif any(w in msg_lower for w in ["associated", "other symptoms", "anything else", "sweat", "clammy", "perspir", "diaphoresis", "cold", "nausea", "sick", "vomit", "throw up", "stomach", "breath", "short of breath", "sob", "dyspnea", "dizzy", "lighthead", "headed", "headache", "vision", "blur", "tingl", "numb", "weakness", "slur"]):
                matching_assoc = [s for s in symptoms[1:] if any(k in s.lower() for k in ["sweat", "clammy", "perspir", "diaphor", "cold", "nausea", "sick", "vomit", "stomach", "throw up", "breath", "dyspnea", "sob", "shortness", "dizzy", "lighthead", "headache", "vision", "blur", "tingl", "numb", "weakness", "slur"])]
                if matching_assoc:
                    response_text = preface + f"Along with the main pain, I've noticed: {'; '.join(matching_assoc)}."
                else:
                    assoc_fact = next((s for s in symptoms if any(k in s.lower() for k in ["nausea", "sick", "vomit", "sweat", "clammy", "breath", "dyspnea"])), None)
                    if assoc_fact:
                        response_text = preface + f"I've also experienced: {assoc_fact}."
                    else:
                        response_text = preface + "No, I haven't noticed any other issues besides the main pain."
                revealed = ["associated_symptoms"]

            # 11. Previous similar episodes
            elif any(w in msg_lower for w in ["before", "previous", "ever had", "history of this", "episode", "prior", "first time"]):
                prior_fact = next((s for s in symptoms + pmh + history_illness if any(k in s.lower() for k in ["prior", "before", "history", "episode", "never experienced", "first time"])), None)
                if prior_fact:
                    response_text = preface + f"Regarding that: {prior_fact}."
                else:
                    response_text = preface + "No, I've never experienced anything like this before. It's completely new."
                revealed = ["past_medical_history"]
                state.memory.add_event("no_prior_similar_episode", 0.7, "question_answered")

            # 12. Smoking
            elif any(w in msg_lower for w in ["smok", "cigarette", "tobacco", "pack"]):
                smoke_fact = next((f for f in social_h if any(k in f.lower() for k in ["smoke", "cigarette", "tobacco", "smoker", "pack"])), None)
                if smoke_fact:
                    if any(k in smoke_fact.lower() for k in ["non-smoker", "doesn't smoke", "never smoke", "no smoke"]):
                        response_text = preface + f"No: {smoke_fact}."
                    else:
                        response_text = preface + f"Yes: {smoke_fact}."
                else:
                    response_text = preface + "No, I don't smoke."
                revealed = ["lifestyle_risk_factors"]
                state.memory.add_event("smoking", 0.8, "question_answered")

            # 13. Diabetes
            elif any(w in msg_lower for w in ["diabet", "sugar", "blood sugar", "glucose", "insulin"]):
                diab_fact = next((f for f in pmh if any(k in f.lower() for k in ["diabet", "sugar", "glucose", "insulin"])), None)
                if diab_fact:
                    response_text = preface + f"{diab_fact}."
                else:
                    response_text = preface + "No, I don't have diabetes or blood sugar trouble."
                revealed = ["past_medical_history"]
                state.memory.add_event("diabetes", 0.8, "question_answered")

            # 14. Blood Pressure
            elif any(w in msg_lower for w in ["blood pressure", "hypertension", "bp"]):
                bp_fact = next((f for f in pmh if any(k in f.lower() for k in ["hypertension", "blood pressure", "bp"])), None)
                if bp_fact:
                    response_text = preface + f"{bp_fact}."
                else:
                    response_text = preface + "No, I don't think I have high blood pressure."
                revealed = ["past_medical_history"]
                state.memory.add_event("hypertension", 0.7, "question_answered")

            # 15. Other Past Medical History
            elif any(w in msg_lower for w in ["past medical", "history of", "health condition", "other diseases", "illness", "medical history", "cholesterol", "thyroid", "cancer", "stroke", "kidney"]):
                other_pmh = [f for f in pmh if not any(k in f.lower() for k in ["hypertension", "blood pressure", "bp", "diabet", "sugar", "glucose"])]
                if other_pmh and other_pmh != ["Generally healthy, no prior surgeries"]:
                    response_text = preface + f"Here is my past medical history: {', '.join(pmh)}."
                else:
                    response_text = preface + f"I'm generally healthy: {', '.join(pmh)}."
                revealed = ["past_medical_history"]

            # 16. Medications
            elif any(w in msg_lower for w in ["medication", "medicine", "pill", "drug", "take", "prescribed", "dose", "rx"]):
                if meds and meds != ["None regular"] and meds != ["None"]:
                    response_text = preface + f"I take these medications: {', '.join(meds)}."
                else:
                    response_text = preface + "I don't take any regular medications."
                revealed = ["medication_history"]
                state.memory.add_event("medications_disclosed", 0.7, "question_answered")

            # 17. Allergies
            elif any(w in msg_lower for w in ["allerg", "penicillin", "reaction"]):
                if allergies:
                    response_text = preface + f"Regarding allergies: {', '.join(allergies)}."
                else:
                    response_text = preface + "No allergies that I know of."
                revealed = ["allergies"]
                state.memory.add_event("no_allergies", 0.5, "question_answered")

            # 18. Family History
            elif any(w in msg_lower for w in ["family", "father", "mother", "parent", "heart disease", "relative", "hx", "brother", "sister"]):
                if family_h:
                    response_text = preface + f"Well, in my family: {', '.join(family_h)}."
                else:
                    response_text = preface + "No significant family history that I can think of."
                revealed = ["family_history"]
                state.memory.add_event("family_history_shared", 0.9, "question_answered")
                memory_importance = 0.9

            # 19. Alcohol
            elif any(w in msg_lower for w in ["alcohol", "drink", "beer", "wine", "liquor", "booze"]):
                alc_fact = next((f for f in social_h if any(k in f.lower() for k in ["alcohol", "drink", "beer", "wine", "liquor"])), None)
                if alc_fact:
                    response_text = preface + f"{alc_fact}."
                else:
                    response_text = preface + "I don't drink alcohol regularly."
                revealed = ["lifestyle_risk_factors"]

            # 20. Recreational Drugs
            elif any(w in msg_lower for w in ["drug use", "recreational", "substance", "marijuana", "weed", "cocaine", "heroin"]):
                drug_fact = next((f for f in social_h if any(k in f.lower() for k in ["drug", "recreational", "substance", "marijuana", "weed"])), None)
                if drug_fact:
                    response_text = preface + f"{drug_fact}."
                else:
                    response_text = preface + "No, I don't use any recreational drugs."
                revealed = ["lifestyle_risk_factors"]

            # 21. Occupation / Job
            elif any(w in msg_lower for w in ["occupation", "job", "work", "do for a living"]):
                p_occ = self.case_data.get("patient", {}).get("occupation", "office worker")
                job_fact = next((f for f in social_h if any(k in f.lower() for k in ["job", "work", "occupation", "office", "manager", "accountant"])), None)
                if job_fact:
                    response_text = preface + f"I work as a {p_occ}. {job_fact}"
                else:
                    response_text = preface + f"I work as a {p_occ}."
                revealed = ["lifestyle_risk_factors"]

            # 22. Marital / Living status / Kids
            elif any(w in msg_lower for w in ["married", "spouse", "wife", "husband", "live with", "children", "kids"]):
                soc_fact = next((f for f in social_h if any(k in f.lower() for k in ["married", "spouse", "wife", "husband", "live", "children", "kids"])), None)
                if soc_fact:
                    response_text = preface + f"Regarding that context: {soc_fact}."
                else:
                    response_text = preface + f"No significant status there, I live normally."
                revealed = ["lifestyle_risk_factors"]

            # 23. Anxiety / Worries Reasons
            elif any(w in msg_lower for w in ["why are you nervous", "why are you anxious", "why are you worried", "why are you scared", "why are u nervous", "why are u anxious", "why are u worried", "why are u scared"]):
                chief_complaint = self.case_data.get("patient", {}).get("chief_complaint", "discomfort")
                response_text = preface + f"I'm scared because I have this severe {chief_complaint.lower()} and I'm really worried it's something serious or life-threatening. I just want to understand what's happening."
                revealed = ["pain_characteristics"]
                state.memory.add_event("anxiety_reason", 0.8, "question_answered")

            # 24. Reassurance responses
            elif any(w in msg_lower for w in ["dont be nervous", "don't be nervous", "dont be scared", "don't be scared", "dont worry", "don't worry", "dont be anxious", "don't be anxious"]):
                chief_complaint = self.case_data.get("patient", {}).get("chief_complaint", "discomfort")
                response_text = preface + f"I'm trying, doctor. It's just hard not to worry when I'm experiencing this {chief_complaint.lower()}."
                memory_category = "emotional"
                memory_importance = 0.6

            elif any(w in msg_lower for w in ["feel free", "feel comfortable"]):
                chief_complaint = self.case_data.get("patient", {}).get("chief_complaint", "discomfort")
                response_text = preface + f"Thank you, doctor. I'm trying to relax and explain everything clearly. What do you think is causing this {chief_complaint.lower()}?"
                memory_category = "emotional"
                memory_importance = 0.5

            # Generic intelligent fallback with keyless real-time lookup
            else:
                clean_query = student_message.lower()
                for prefix in ["what is ", "what does ", "tell me about ", "do you know what ", "explain "]:
                    if clean_query.startswith(prefix):
                        clean_query = clean_query[len(prefix):]
                clean_query = clean_query.strip("? .")
                
                abstract_val = fetch_realtime_definition(clean_query)
                if abstract_val:
                    if "metformin" in clean_query:
                        response_text = preface + f"I take Metformin for my Type 2 diabetes. My doctor mentioned it's a first-line treatment for sugar control, or as they put it online: '{abstract_val}'"
                    elif "lisinopril" in clean_query:
                        response_text = preface + f"Lisinopril is what they prescribed for my blood pressure. According to my doctor, it's an ACE inhibitor: '{abstract_val}'"
                    elif "atorvastatin" in clean_query:
                        response_text = preface + f"I take Atorvastatin for my high cholesterol. It's to protect my arteries: '{abstract_val}'"
                    elif "troponin" in clean_query:
                        response_text = preface + f"A troponin test? I think the nurses mentioned that's a protein checked during a heart attack: '{abstract_val}'"
                    elif "ecg" in clean_query or "electrocardiogram" in clean_query:
                        response_text = preface + f"An ECG is that heart tracing test. I remember reading that: '{abstract_val}'"
                    else:
                        response_text = preface + f"I'm not a doctor, but I recall reading lookup info about that: '{abstract_val}'"
                    memory_category = "clinical"
                    memory_importance = 0.5
                else:
                    emotion_label = state.emotion.get_label()
                    chief_complaint = self.case_data.get("patient", {}).get("chief_complaint", "discomfort")
                    if emotion_label in ["Frightened", "Distressed"]:
                        response_text = (
                            preface + "I'm sorry, I... I'm having a hard time concentrating. "
                            "I'm just really scared right now. What's happening to me?"
                        )
                    elif emotion_label == "Anxious":
                        response_text = preface + "I'm not sure about that. Could you explain what you mean? I just want to understand what's going on."
                    elif state.emotion.trust < 35:
                        response_text = preface + "Why do you need to know that? Is it important for what's happening to me?"
                    else:
                        response_text = (
                            preface + "I'm not sure I understand that question, doctor. "
                            f"I'm just trying to focus on this {chief_complaint.lower()} right now."
                        )

        # Apply emotional spikes for existential threat (if alarmist/frightening)
        if detect_existential_threat(student_message):
            spike = compute_existential_threat_emotion_spike(
                fear_of_death=state.personality.fear_of_death,
                emotional_sensitivity=state.personality.emotional_sensitivity,
            )
            emotion_delta.update(spike)

        # Apply the final emotion update
        new_emotion = EmotionalState.from_dict(state.emotion.to_dict())
        new_emotion.apply_update(emotion_delta)

        return {
            "response": response_text,
            "emotion_update": new_emotion.to_dict(),
            "revealed_information": revealed,
            "memory_event": {
                "event": f"student_asked: {student_message[:80]}",
                "importance": memory_importance,
                "category": memory_category,
            },
            "communication_state": new_emotion.get_label().lower(),
            "student_communication_classification": intent,
        }

    def _apply_result_to_state(
        self,
        state: PatientAgentState,
        result: Dict[str, Any],
        student_style: str,
    ) -> PatientAgentState:
        """Apply LLM/demo result back to agent state."""
        # Update emotion
        emotion_update = result.get("emotion_update", {})
        if emotion_update:
            if all(isinstance(v, (int, float)) for v in emotion_update.values()):
                # LLM returned absolute values — set them directly
                state.emotion.set_values(emotion_update)
            else:
                # Fallback — treat as deltas
                state.emotion.apply_update(emotion_update)

        # Naturally decay shock each turn (shock is acute, not chronic)
        if state.emotion.shock > 0:
            decay = max(5, state.emotion.shock // 4)  # decay 25% per turn
            state.emotion.apply_update({"shock": -decay})

        # Add memory event
        mem_event = result.get("memory_event")
        if mem_event and isinstance(mem_event, dict):
            state.memory.add_event(
                event=mem_event.get("event", ""),
                importance=float(mem_event.get("importance", 0.5)),
                category=mem_event.get("category", "general"),
            )

        # Record student communication style
        state.add_communication_event(student_style)

        # Mark revealed facts
        for fact in result.get("revealed_information", []):
            state.mark_fact_revealed(fact)

        # Record emotional event if notable
        emotion_label = state.emotion.get_label()
        if emotion_label in ["Shocked", "Frightened", "Distressed", "Reassured"] or student_style in ["alarmist", "dismissive"]:
            state.add_emotional_event(
                description=f"Student ({student_style}) → Patient: {emotion_label}",
                emotion_label=emotion_label,
                turn=state.turn_count,
            )

        # Advance phase
        state.advance_phase()

        return state

    def _get_fallback_text(self, student_style: str) -> str:
        """Provide a minimal fallback response text."""
        if student_style == "alarmist":
            return "What do you mean? Is something seriously wrong? Please explain."
        elif student_style == "dismissive":
            return "I... I'll try to answer. I just need to know what's happening."
        elif student_style == "empathetic":
            return "Thank you. I'm just really worried about this chest pressure."
        return "I'm not sure I understand. Could you explain that?"

    def generate_investigation_reaction(
        self,
        state: PatientAgentState,
        investigation_name: str,
    ) -> Tuple[PatientAgentState, Optional[str]]:
        """
        Generate an optional patient reaction to an investigation being ordered.
        Returns (updated_state, reaction_text_or_None)
        """
        investigation_lower = investigation_name.lower()

        # Only react to notable investigations
        reaction = None

        if state.emotion.anxiety > 40:
            if "ecg" in investigation_lower or "electrocardiogram" in investigation_lower:
                reaction = "An ECG? Is there something wrong with my heart? That's what I was afraid of..."
            elif "troponin" in investigation_lower or "cardiac" in investigation_lower:
                if state.emotion.fear > 50:
                    reaction = "What is that test for? Is it to check if something's happened to my heart?"
                else:
                    reaction = "What does this blood test show?"
            elif "ct" in investigation_lower or "scan" in investigation_lower:
                reaction = "A CT scan? Is that serious? Why do I need one of those?"
            elif "x-ray" in investigation_lower or "cxr" in investigation_lower:
                reaction = "Do I need a chest X-ray? What are you looking for?"

        if reaction:
            state.memory.add_event(
                f"investigation_reaction_{investigation_lower[:20]}",
                importance=0.5,
                category="clinical"
            )
            state.add_emotional_event(
                description=f"Investigation ordered: {investigation_name}",
                emotion_label=state.emotion.get_label(),
                turn=state.turn_count,
            )

        return state, reaction
