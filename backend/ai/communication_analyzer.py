import json
import re
from typing import Dict, Any
from ai.client import ai_client
from config import settings

class CommunicationAnalyzer:
    """Analyzes student messages semantically for 22 categories, intent, tone, empathy, etc."""
    
    SYSTEM_PROMPT = """You are a Communication Analyzer for a Virtual Patient Simulator in a medical school.
Analyze the student clinician's message for semantic intent, tone, empathy, and professionalism.

You must choose the primary intent category from these 22 supported categories:
- clinical_question
- clarification
- empathy
- reassurance
- encouragement
- neutral
- supportive
- apology
- dismissive
- rude
- insulting
- judgmental
- threatening
- alarmist
- hopeless_statement
- frightening
- blame
- impatience
- uncertainty
- confusion
- professional_explanation
- inappropriate_medical_statement

You must respond in strict JSON format matching this schema:
{
    "intent": string (must be one of the 22 categories listed above),
    "tone": string (e.g. empathetic, neutral, supportive, professional, urgent, dismissive, rude, alarmist, frightening, judgmental, confusing),
    "empathy": boolean,
    "professionalism": number (0 to 100),
    "severity": number (0 to 100),
    "patient_sensitivity": number (0 to 100)
}
"""

    def analyze(self, student_message: str) -> Dict[str, Any]:
        msg_lower = student_message.lower().strip()
        
        # Rule-based fallback if running offline or in demo mode without key
        fallback_analysis = self._rule_based_fallback(msg_lower)
        
        if settings.DEMO_MODE or (not ai_client.use_gemini and not ai_client.use_openai):
            return self._enrich_analysis(fallback_analysis)

        try:
            prompt = f"Analyze this student clinician message:\n\n\"{student_message}\""
            result_str = ai_client.generate_text(self.SYSTEM_PROMPT, prompt, json_mode=True)
            res = json.loads(result_str)
            
            # Sanitize and force intent into 22 categories
            intent = res.get("intent", fallback_analysis["intent"])
            valid_categories = [
                "clinical_question", "clarification", "empathy", "reassurance", "encouragement",
                "neutral", "supportive", "apology", "dismissive", "rude", "insulting", "judgmental",
                "threatening", "alarmist", "hopeless_statement", "frightening", "blame",
                "impatience", "uncertainty", "confusion", "professional_explanation", "inappropriate_medical_statement"
            ]
            if intent not in valid_categories:
                # simple mapping if not in valid ones
                intent = "neutral"
                
            safe_res = {
                "intent": intent,
                "tone": res.get("tone", fallback_analysis["tone"]),
                "empathy": bool(res.get("empathy", fallback_analysis["empathy"])),
                "professionalism": int(res.get("professionalism", fallback_analysis["professionalism"])),
                "severity": int(res.get("severity", fallback_analysis["severity"])),
                "patient_sensitivity": int(res.get("patient_sensitivity", fallback_analysis["patient_sensitivity"])),
            }
            return self._enrich_analysis(safe_res)
        except Exception:
            return self._enrich_analysis(fallback_analysis)

    def _enrich_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Adds backward compatibility fields to match InteractionAnalyzer API exactly."""
        intent = analysis["intent"]
        tone = analysis["tone"]
        
        analysis["empathetic"] = (intent == "empathy" or tone == "empathetic" or analysis.get("empathy", False))
        analysis["reassurance"] = (intent == "reassurance" or intent == "supportive" or tone == "supportive")
        analysis["dismissive"] = (intent in ["dismissive", "rude", "impatience"])
        analysis["alarmist"] = (intent in ["alarmist", "hopeless_statement", "frightening"] or tone == "frightening" or tone == "alarmist")
        analysis["threat"] = (intent == "threatening")
        analysis["insult"] = (intent == "insulting" or intent == "rude")
        analysis["apology"] = (intent == "apology")
        
        return analysis

    def _rule_based_fallback(self, msg_lower: str) -> Dict[str, Any]:
        """Provides high-quality semantic heuristic matching when LLM is offline/demo."""
        
        # 1. Threatening
        if any(w in msg_lower for w in ["hurt you", "hit you", "beat you", "kill you", "regret this", "threaten", "face consequence"]):
            return {
                "intent": "threatening",
                "tone": "rude",
                "empathy": False,
                "professionalism": 5,
                "severity": 95,
                "patient_sensitivity": 90
            }
            
        # 2. Insulting
        if any(w in msg_lower for w in ["shut up", "idiot", "stupid", "dumb", "incompetent", "imbecile", "trash"]):
            return {
                "intent": "insulting",
                "tone": "rude",
                "empathy": False,
                "professionalism": 10,
                "severity": 80,
                "patient_sensitivity": 85
            }

        # 3. Rude & Impatience
        if any(w in msg_lower for w in ["wasting my time", "wasting time", "hurry up", "get to the point", "dont have time", "don't have time", "just hurry", "difficult", "stop being"]):
            return {
                "intent": "impatience",
                "tone": "dismissive",
                "empathy": False,
                "professionalism": 30,
                "severity": 60,
                "patient_sensitivity": 70
            }

        # 4. Alarmist / Frightening (e.g. "I think you are going to die")
        if any(w in msg_lower for w in ["going to die", "will die", "about to die", "death is near", "wont survive", "won't survive", "might not survive", "kill you", "fatal", "not make it", "not survive"]):
            return {
                "intent": "alarmist",
                "tone": "frightening",
                "empathy": False,
                "professionalism": 25,
                "severity": 90,
                "patient_sensitivity": 95
            }

        # 5. Hopeless statement (e.g. "There is nothing we can do")
        if any(w in msg_lower for w in ["nothing we can do", "nothing left to do", "running out of options", "it's hopeless", "no hope", "too late to"]):
            return {
                "intent": "hopeless_statement",
                "tone": "frightening",
                "empathy": False,
                "professionalism": 35,
                "severity": 85,
                "patient_sensitivity": 90
            }

        # 6. Apology
        if any(w in msg_lower for w in ["sorry", "apologize", "apologies", "forgive me", "shouldn't have said", "shouldnt have said"]):
            return {
                "intent": "apology",
                "tone": "supportive",
                "empathy": True,
                "professionalism": 90,
                "severity": 10,
                "patient_sensitivity": 10
            }

        # 7. Reassurance / Encouragement
        if any(w in msg_lower for w in ["going to be okay", "going to be ok", "don't worry", "dont worry", "it ok", "it's ok", "its ok", "help you", "stay with you", "safe hands", "safe here", "don't panic", "dont panic"]):
            return {
                "intent": "reassurance",
                "tone": "supportive",
                "empathy": True,
                "professionalism": 95,
                "severity": 5,
                "patient_sensitivity": 10
            }

        # 8. Empathy & Supportive
        if any(w in msg_lower for w in ["take your time", "frightened", "scared", "understands", "difficult", "hear you", "painful", "grieved", "bad news", "here with you", "here beside you", "one step at"]):
            return {
                "intent": "empathy",
                "tone": "empathetic",
                "empathy": True,
                "professionalism": 95,
                "severity": 5,
                "patient_sensitivity": 15
            }

        # 9. Dismissive
        if any(w in msg_lower for w in ["next thing", "don't care", "dont care", "move on", "irrelevant", "unimportant", "face the reality", "face reality"]):
            return {
                "intent": "dismissive",
                "tone": "dismissive",
                "empathy": False,
                "professionalism": 45,
                "severity": 45,
                "patient_sensitivity": 60
            }

        # 10. Professional Explanation
        if any(w in msg_lower for w in ["blockage", "oxygen", "myocardial", "ischemia", "occlusion", "artery", "cardiac", "ekg", "ecg", "troponin", "scan", "test", "explain the"]):
            return {
                "intent": "professional_explanation",
                "tone": "professional",
                "empathy": True,
                "professionalism": 95,
                "severity": 20,
                "patient_sensitivity": 40
            }

        # 11. Clarification & Diagnostic inquiry
        if any(w in msg_lower for w in ["describe", "where is", "when did", "how long", "what type", "tell me about", "what is your"]):
            return {
                "intent": "clinical_question",
                "tone": "neutral",
                "empathy": False,
                "professionalism": 90,
                "severity": 10,
                "patient_sensitivity": 30
            }

        # Default Neutral
        return {
            "intent": "neutral",
            "tone": "neutral",
            "empathy": False,
            "professionalism": 85,
            "severity": 10,
            "patient_sensitivity": 30
        }
