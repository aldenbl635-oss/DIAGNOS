"""
Patient Agent — main orchestrator for the AI virtual patient.
Reconstructs the virtual patient's reaction based on modular interactions:
Student Message → InteractionAnalyzer → Transition Engine → RAG → LLM Response → Volun. Check
"""

import os
import json
import random
from typing import Dict, Any, List, Optional, Tuple

from ai.client import ai_client
from ai.patient_state import PatientAgentState
from ai.patient_emotion import EmotionalState
from ai.patient_memory import PatientMemory, MemoryEvent
from ai.patient_personality import PersonalityProfile
from ai.interaction_analyzer import InteractionAnalyzer
from data.adapters import MedicalKnowledgeRetriever, DialogueRetriever, ClinicalCaseRetriever
from ai.patient_reasoning import (
    detect_existential_threat,
    compute_existential_threat_emotion_spike,
    parse_agent_response,
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
    c_state = case_data.get("clinical_state", {})
    history = case_data.get("history", {})
    presentation = case_data.get("presentation", {})

    symptoms = c_state.get("symptoms") or facts.get("symptoms", [])
    onset = c_state.get("onset") or facts.get("onset", "")
    pmh = history.get("past_medical_history") or facts.get("past_medical_history", [])
    meds = history.get("medications") or facts.get("medications", [])
    allergies = history.get("allergies") or facts.get("allergies", [])
    family_h = history.get("family_history") or facts.get("family_history", [])
    social_h = history.get("social_history", []) or history.get("lifestyle_risk_factors", []) or facts.get("social_history", [])
    excl = c_state.get("associated_symptoms") or facts.get("associated_symptoms", [])

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

    add_section("Chief Complaint & Symptoms", symptoms)
    if onset:
        add_section("Onset", onset)
    add_section("Past Medical History", pmh)
    add_section("Medications", meds)
    add_section("Allergies", allergies)
    add_section("Family History", family_h)
    add_section("Social & Lifestyle History", social_h)
    add_section("Associated Symptoms", excl)
    add_section("Review of Systems", facts.get("review_of_systems"))

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


def check_keyword_match(message: str, keywords: List[str]) -> bool:
    import re
    msg_lower = message.lower()
    
    # Anatomical and occupational keywords check to filter out non-clinical contexts
    gated_kws = ["leg", "arm", "jaw", "neck", "back", "groin", "thigh", "job", "work", "pack", "lifestyle", "rest", "worse", "better", "dose", "rx", "pill", "drug", "take"]
    has_gated_kw = False
    for kw in keywords:
        if kw.lower().strip() in gated_kws:
            kw_clean = kw.lower().strip()
            # Check if this keyword is actually present in the message with appropriate word boundary
            if kw_clean in ["leg", "arm", "jaw", "neck", "back", "groin", "thigh", "job", "work", "pack", "lifestyle", "rest", "worse", "better", "dose", "rx", "pill", "drug", "take"]:
                if re.search(rf"\b{re.escape(kw_clean)}s?\b", msg_lower):
                    has_gated_kw = True
                    break
            else:
                if re.search(rf"\b{re.escape(kw_clean)}", msg_lower):
                    has_gated_kw = True
                    break
                    
    if has_gated_kw:
        # Require patient focus or clinical context words
        context_words = ["you", "your", "yours", "u", "ur", "my", "i ", "i'm", "patient", "pain", "discomfort", "hurt", "ache", "radiat", "spread", "go", "move", "travel", "shoot", "symptom", "feel", "feeling", "feels", "problem", "issue", "swelling", "swell", "numb", "tingl", "weak"]
        if not any(re.search(rf"\b{re.escape(cw)}", msg_lower) for cw in context_words):
            return False

    for kw in keywords:
        kw_clean = kw.lower().strip()
        if not kw_clean:
            continue
        if " " in kw_clean:
            if kw_clean in msg_lower:
                return True
        else:
            # Short anatomical and temporal keywords check word boundary with optional 's' plural character
            if kw_clean in ["leg", "arm", "jaw", "neck", "back", "groin", "thigh", "time", "day", "hour", "week", "job", "work", "pack", "lifestyle", "rest", "worse", "better", "dose", "rx", "pill", "drug", "take", "bp", "sex", "age", "dob", "sob", "hi"]:
                if re.search(rf"\b{re.escape(kw_clean)}s?\b", msg_lower):
                    return True
            else:
                # Prefix matching to allow e.g. "smoking" for "smok", "diabetes" for "diabet"
                if re.search(rf"\b{re.escape(kw_clean)}", msg_lower):
                    return True
    return False


class PatientAgent:
    """
    The AI Virtual Patient Agent.
    Generates contextually appropriate, emotionally reactive, memory-aware
    patient responses based on student input.
    """

    def __init__(self, case_data: Dict[str, Any]):
        self.case_data = case_data
        self.patient = case_data.get("patient", {})
        self.presentation = case_data.get("presentation", {})
        self.system_prompt_template = _load_prompt("patient_system.txt")
        self.clinical_facts_text = _build_clinical_facts_text(case_data)

        # Retrievers Definition (PART 22 - RAG / RETRIEVAL)
        self.knowledge_retriever = MedicalKnowledgeRetriever()
        self.dialogue_retriever = DialogueRetriever()
        self.case_retriever = ClinicalCaseRetriever(case_data)
        self.interaction_analyzer = InteractionAnalyzer()

    def _build_system_prompt(self, state: PatientAgentState, dialogue_grounding: str, clinical_grounding: str) -> str:
        """Construct the full system prompt for this turn, embedding grounding resources."""
        name = self.patient.get("name", "the patient")
        personality_narrative = state.personality.to_narrative()

        beliefs_text = "\n".join(
            f"- {b}" for b in state.beliefs
        ) if state.beliefs else "You have not formed any specific beliefs yet."

        goals_text = "\n".join(
            f"- {g}" for g in state.goals
        ) if state.goals else "Your main goal is to understand what is happening."

        # Grab dynamic description
        emotional_desc = state.emotion.to_prompt_description()
        memory_summary = state.memory.get_relevant_summary()

        # Combine clinical facts with retrieved MIMIC clinical notes / guidelines
        facts_text = self.clinical_facts_text
        if clinical_grounding:
            facts_text += f"\n\n{clinical_grounding}"
        if dialogue_grounding:
            facts_text += f"\n\n{dialogue_grounding}"

        cc = self.presentation.get("chief_complaint") or self.patient.get("chief_complaint", "discomfort")

        return self.system_prompt_template.format(
            patient_name=name,
            patient_age=self.patient.get("age") or self.case_data.get("patient_age", "unknown"),
            patient_sex=self.patient.get("sex") or self.case_data.get("patient_sex", "unknown"),
            patient_occupation=self.patient.get("occupation", "unknown"),
            chief_complaint=cc,
            clinical_facts=facts_text,
            personality_narrative=personality_narrative,
            patient_beliefs=beliefs_text,
            patient_goals=goals_text,
            emotional_state_description=emotional_desc,
            memory_summary=memory_summary,
            simulation_phase=state.simulation_phase,
        )

    def _get_grounding_examples_text(self, intent: str, msg: str) -> str:
        try:
            import os
            import json
            pb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "patient_behavior", "synthetic_behaviors.json")
            if not os.path.exists(pb_path):
                return ""
            with open(pb_path, "r", encoding="utf-8") as f:
                behaviors = json.load(f)
            
            # Find up to 3 examples matching this intent (or nearby categories)
            matches = [ex for ex in behaviors if ex["communication_analysis"]["intent"] == intent]
            if len(matches) < 2:
                matches = behaviors[:3]
            else:
                matches = matches[:3]
                
            lines = ["\n== BEHAVIORAL GROUNDING EXAMPLES (FOR PSYCHOLOGICAL ACCURACY) =="]
            p_name = self.patient.get("name", "patient")
            for idx, ex in enumerate(matches, 1):
                st_msg = ex.get("student_message", "")
                ex_resp = ex.get("patient_response", "")
                ex_resp = ex_resp.replace("Robert Vance", p_name).replace("Vance", p_name.split()[-1])
                ex_effect = ex.get("behavioral_effect", "")
                lines.append(f"Example {idx}:")
                lines.append(f"  Student said: \"{st_msg}\"")
                lines.append(f"  Expected response style: \"{ex_resp}\"")
                lines.append(f"  Psychological effect: {ex_effect}\n")
            return "\n".join(lines)
        except Exception as e:
            print("Error building grounding examples text:", e)
            return ""

    def _volunteer_information(self, state: PatientAgentState, response_text: str) -> Tuple[str, List[str]]:
        """PART 15 - PATIENT VOLUNTEERING INFORMATION
        Patients occasionally recall or mention details if trust & cooperation are high.
        """
        volunteered_count = sum(1 for e in state.memory.events if "volunteered" in e.event)
        
        # Check cooperation and trust levels (both must show positive intent)
        if state.emotion.trust > 60 and state.emotion.cooperation > 60 and volunteered_count < 2:
            facts = self.case_data.get("clinical_facts", {})
            c_state = self.case_data.get("clinical_state", {})
            history = self.case_data.get("history", {})

            symptoms = c_state.get("symptoms", []) or facts.get("symptoms", [])
            associated = c_state.get("associated_symptoms", []) or facts.get("associated_symptoms", [])
            pmh = history.get("past_medical_history", []) or facts.get("past_medical_history", [])
            
            # Identify details not yet reported in conversation or response text
            candidates = []
            for s in associated:
                if not state.memory.has_answered(s[:15]) and s.lower() not in response_text.lower():
                    candidates.append((s, "associated_symptoms"))
            for p in pmh:
                if not state.memory.has_answered(p[:15]) and p.lower() not in response_text.lower():
                    # Ignore generic healthy text
                    if "generally healthy" not in p.lower():
                        candidates.append((p, "past_medical_history"))

            if candidates:
                # Select a candidate deterministically using turn count to ensure test completeness
                idx = state.turn_count % len(candidates)
                choice, cat = candidates[idx]
                
                phrase = f" Also, doctor... I forgot to mention something. {choice}"
                state.memory.add_event(f"volunteered_{cat}_{choice[:25]}", importance=0.8, category="question_answered")
                return response_text + phrase, [cat]

        return response_text, []

    def generate_response(
        self,
        state: PatientAgentState,
        conversation_history: List[Dict[str, str]],
        student_message: str,
        event_context: Optional[str] = None,
    ) -> Tuple[PatientAgentState, Dict[str, Any]]:
        """
        Main logic E2E processing student input to yield modular response.
        """
        try:
            # Record student question in short term logs
            state.memory.add_turn("student", student_message)

            # 1. ANALYZE STUDENT MESSAGE (PART 1, PART 10)
            com_analysis = self.interaction_analyzer.analyze(student_message)
            student_style = com_analysis["intent"]

            # Existential threat checks (Pre-calculations)
            is_existential_threat = detect_existential_threat(student_message)
            if is_existential_threat:
                spike = compute_existential_threat_emotion_spike(
                    fear_of_death=state.personality.fear_of_death,
                    emotional_sensitivity=state.personality.emotional_sensitivity,
                )
                state.emotion.set_values({k: v for k, v in spike.items() if v > 0})
                if spike.get("trust", 0) < 0:
                    state.emotion.apply_update({"trust": spike["trust"]})

            # 2. TRANSITION EMOTIONS (PART 9)
            emotion_delta = state.emotion.calculate_transitions(com_analysis, personality=state.personality, turn_count=state.turn_count)
            state.emotion.apply_update(emotion_delta)

            # 3. RAG LAYER RETRIEVALS (PART 22 - RAG / RETRIEVAL)
            dialogue_grounding = self.dialogue_retriever.get_conversational_grounding(student_message)
            clinical_grounding = self.knowledge_retriever.retrieve_guidelines(
                self.case_data.get("clinical_state", {}).get("symptoms", []) or self.case_data.get("clinical_facts", {}).get("symptoms", []),
                self.case_data.get("history", {}).get("medications", []) or self.case_data.get("clinical_facts", {}).get("medications", [])
            )

            # 4. CHOOSE RESOLUTION (LLM OR DEMO ACCORDING TO DEMO_MODE SETTINGS)
            effective_message = student_message
            if event_context:
                effective_message = f"[System event: {event_context}]\n\nStudent says: {student_message}"

            if settings.DEMO_MODE:
                try:
                    result = self._demo_response(state, student_message, student_style, conversation_history, com_analysis)
                except Exception as ex_demo:
                    print(f"Error executing _demo_response: {ex_demo}. Using default fallback.")
                    result = {
                        "response": "I'm not sure I understand that question, doctor. Let's focus on my chest discomfort.",
                        "emotion_update": {},
                        "revealed_information": [],
                        "memory_event": {
                            "event": "demo_fallback_recovery",
                            "importance": 0.5,
                            "category": "general"
                        },
                        "communication_state": state.emotion.get_label().lower() if hasattr(state, "emotion") else "guarded",
                        "student_communication_classification": student_style,
                    }
            else:
                try:
                    # Build system prompt with RAG grounding attached
                    system_prompt = self._build_system_prompt(state, dialogue_grounding, clinical_grounding)
                    conversation_text = _build_conversation_text(conversation_history)
                    grounding_examples = self._get_grounding_examples_text(student_style, student_message)
                    user_prompt = (
                        f"Recent conversation:\n{conversation_text}\n\n"
                        f"Student's latest message: {student_message}\n\n"
                        f"Student's communication pattern: {student_style} (severity: {com_analysis.get('severity', 50)}/100)\n"
                        f"{grounding_examples}\n\n"
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
                    parsed["student_communication_classification"] = student_style

                    # Synchronize states
                    new_emotions = parsed.get("emotion_update", {})
                    if new_emotions:
                        state.emotion.set_values(new_emotions)

                    result = parsed
                except Exception as e:
                    print(f"PatientAgent LLM error: {e}. Falling back to demo engine.")
                    try:
                        result = self._demo_response(state, student_message, student_style, conversation_history, com_analysis)
                    except Exception as ex_demo_inner:
                        print(f"Inner demo response error during fallback: {ex_demo_inner}")
                        result = {
                            "response": "I'm not sure I understand that question, doctor. Let's focus on my chest discomfort.",
                            "emotion_update": {},
                            "revealed_information": [],
                            "memory_event": {
                                "event": "llm_fallback_recovery",
                                "importance": 0.5,
                                "category": "general"
                            },
                            "communication_state": state.emotion.get_label().lower() if hasattr(state, "emotion") else "guarded",
                            "student_communication_classification": student_style,
                        }

            # 5. VOLUNTEERING VERIFICATION (PART 15)
            response_text = result.get("response", "")
            volunteered_text, extra_revealed = self._volunteer_information(state, response_text)
            result["response"] = volunteered_text
            
            # Merge revealed items
            revealed_facts_list = list(result.get("revealed_information", []))
            for item in extra_revealed:
                if item not in revealed_facts_list:
                    revealed_facts_list.append(item)
            result["revealed_information"] = revealed_facts_list

            # Persist results to state object
            updated_state = self._apply_result_to_state(state, result, student_style)

            # Add response trace to short term logs
            updated_state.memory.add_turn("patient", result["response"])

            # Create structured output log
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

            internal_structured_info = {
                "patient_response": result.get("response", ""),
                "communication_analysis": {
                    "intent": com_analysis["intent"],
                    "tone": com_analysis["tone"],
                    "severity": com_analysis["severity"],
                    "professionalism": com_analysis["professionalism"],
                    "empathetic": com_analysis["empathetic"],
                    "reassurance": com_analysis["reassurance"],
                    "dismissive": com_analysis["dismissive"],
                    "alarmist": com_analysis["alarmist"],
                    "threat": com_analysis["threat"],
                    "insult": com_analysis["insult"],
                    "apology": com_analysis["apology"]
                },
                "emotional_update": updated_state.emotion.to_dict(),
                "behavior": updated_state.emotion.get_behavioral_cue(),
                "memory_event": result.get("memory_event", {}).get("event") if result.get("memory_event") else None,
                "patient_state": label.lower()
            }
            print("\n=== INTERNAL AGENT STRUCTURED OUTPUT ===")
            print(json.dumps(internal_structured_info, indent=2))
            print("=========================================\n")

            # Build output properties
            output = {
                "response": result.get("response", ""),
                "emotion_label": updated_state.emotion.get_label(),
                "emotional_cue": updated_state.emotion.get_behavioral_cue(),
                "student_communication_classification": student_style,
                "communication_state": com_state,
                "revealed_information": result.get("revealed_information", []),
            }

            return updated_state, output
        except Exception as e_global:
            import traceback
            print(f"GLOBAL EXCEPTION CAUGHT IN generate_response: {e_global}")
            traceback.print_exc()
            
            # Construct a safe emergency response dictionary
            emergency_text = "I'm not sure how to respond to that, doctor. Let's focus on my chest discomfort."
            
            try:
                state.memory.add_turn("patient", emergency_text)
                state.advance_phase()
            except Exception:
                pass
                
            emergency_output = {
                "response": emergency_text,
                "emotion_label": state.emotion.get_label() if hasattr(state, "emotion") else "Anxious",
                "emotional_cue": state.emotion.get_behavioral_cue() if hasattr(state, "emotion") else "The patient is fidgeting and seems increasingly nervous.",
                "student_communication_classification": "neutral",
                "communication_state": "guarded",
                "revealed_information": []
            }
            return state, emergency_output

    def _demo_response(
        self,
        state: PatientAgentState,
        student_message: str,
        student_style: str,
        conversation_history: List[Dict[str, str]],
        com_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Offline patient response engine — fully LLM-free.
        Delegates to OfflinePatientResponder which uses semantic classification +
        structured patient context to generate natural, human-like responses
        for ANY student message without a generic fallback.
        """
        from ai.offline_responder import OfflinePatientResponder
        responder = OfflinePatientResponder(self.case_data)
        return responder.respond(student_message, state, com_analysis)

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
                state.emotion.set_values(emotion_update)
            else:
                state.emotion.apply_update(emotion_update)

        # Natural decay of shock
        if state.emotion.shock > 0:
            decay = max(5, state.emotion.shock // 4)
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
        """
        investigation_lower = investigation_name.lower()
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
