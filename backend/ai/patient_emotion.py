"""
Emotional state engine for the virtual patient.
All values are on a 0-100 scale (internal simulation state).
These values are NEVER directly exposed to the student.
The student only sees a derived human-readable label and behavioral cues.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

EMOTION_LABEL_THRESHOLDS = [
    # (label, condition_fn) — evaluated in order; first match wins
    ("Shocked",     lambda e: e.shock >= 70),
    ("Frightened",  lambda e: e.fear >= 75 or e.distress >= 80),
    ("Angry",       lambda e: e.anger >= 50),
    ("Distressed",  lambda e: e.distress >= 60 or (e.fear >= 55 and e.anxiety >= 55)),
    ("Anxious",     lambda e: e.anxiety >= 55 or e.fear >= 45),
    ("Confused",    lambda e: e.confusion >= 50),
    ("Concerned",   lambda e: e.anxiety >= 35 or e.fear >= 25 or e.confusion >= 40),
    ("Reassured",   lambda e: e.trust >= 70 and e.hope >= 60 and e.anxiety < 35 and e.distress < 35),
    ("Calm",        lambda e: True),  # default
]

@dataclass
class EmotionalState:
    fear: int = 30
    anxiety: int = 35
    trust: int = 50
    confusion: int = 20
    distress: int = 25
    hope: int = 65
    anger: int = 10
    embarrassment: int = 10
    pain: int = 45
    shock: int = 0        # acute shock / disbelief (spiked by sudden alarming statements)
    sadness: int = 10      # grief / emotional heaviness
    cooperation: int = 60  # Cooperation score dynamically affected by tone/intent
    frustration: int = 15  # Patient frustration level (continuous variable)

    def _clamp(self, value: int) -> int:
        return max(0, min(100, value))

    def apply_update(self, delta: Dict[str, int]) -> None:
        """Apply a delta dict of {emotion: delta_value} to current state."""
        for key, change in delta.items():
            if hasattr(self, key):
                current = getattr(self, key)
                setattr(self, key, self._clamp(current + change))

    def calculate_transitions(self, analysis: Dict[str, Any], personality: Optional[Any] = None, turn_count: int = 1) -> Dict[str, int]:
        """PART 3 & 9 - EMOTIONAL TRANSITIONS
        Calculate the delta changes based on semantic analyzer output.
        The changes are NOT fixed; they scale based on:
        - patient personality (sensitivities, fears, medical trust, cooperativeness)
        - analytical severity of the student comment
        - current emotional levels
        - turn count (representing depth of interaction)
        """
        delta = {}
        
        # 1. Compute dynamic factors
        sensitivity = (personality.emotional_sensitivity / 50.0) if personality else 1.0
        distrust = (personality.distrust_of_medical / 50.0) if personality else 1.0
        fear_death_factor = (personality.fear_of_death / 50.0) if personality else 1.0
        coop_base = (personality.cooperativeness / 50.0) if personality else 1.0
        
        # Severity scaling factor (default to 50 / 50 = 1.0)
        sev_factor = (analysis.get("severity", 50) / 50.0)
        
        # Dampen negative changes slightly if trust is high and turns are advanced (established rapport)
        rapport_dampening = 1.0
        if self.trust > 70 and turn_count > 4:
            rapport_dampening = 0.65

        intent = analysis.get("intent")
        tone = analysis.get("tone")

        # 2. Match semantic profiles
        
        # Empathy / Supportive
        if analysis.get("empathetic") or intent == "empathy" or intent == "supportive":
            delta["trust"] = int(12 * (1.0 / max(0.4, distrust)) * sev_factor)
            delta["fear"] = -int(8 * sensitivity * sev_factor)
            delta["anxiety"] = -int(8 * sensitivity * sev_factor)
            delta["distress"] = -int(8 * sensitivity * sev_factor)
            delta["cooperation"] = int(10 * coop_base * sev_factor)
            delta["frustration"] = -int(15 * sev_factor)
            delta["anger"] = -int(10 * sev_factor)

        # Reassurance / Encouragement
        if analysis.get("reassurance") or intent == "reassurance" or intent == "encouragement":
            delta["trust"] = int(10 * (1.0 / max(0.4, distrust)) * sev_factor)
            delta["fear"] = -int(12 * sensitivity * sev_factor)
            delta["anxiety"] = -int(10 * sensitivity * sev_factor)
            delta["cooperation"] = int(8 * coop_base * sev_factor)
            delta["frustration"] = -int(10 * sev_factor)
            delta["hope"] = int(15 * sev_factor)

        # Dismissive / Face Reality
        if analysis.get("dismissive") or intent == "dismissive":
            delta["trust"] = -int(15 * distrust * sev_factor * rapport_dampening)
            delta["distress"] = int(12 * sensitivity * sev_factor)
            delta["cooperation"] = -int(8 * sev_factor * rapport_dampening)
            delta["frustration"] = int(15 * sensitivity * sev_factor)
            delta["anger"] = int(10 * sensitivity * sev_factor)

        # Insult / Rude
        if analysis.get("insult") or intent == "insulting" or tone == "rude":
            delta["anger"] = int(25 * sensitivity * sev_factor)
            delta["trust"] = -int(20 * distrust * sev_factor * rapport_dampening)
            delta["cooperation"] = -int(18 * sev_factor * rapport_dampening)
            delta["frustration"] = int(25 * sensitivity * sev_factor)
            delta["distress"] = int(10 * sensitivity * sev_factor)

        # Threat
        if analysis.get("threat") or intent == "threatening":
            delta["fear"] = int(35 * sensitivity * sev_factor)
            delta["anxiety"] = int(25 * sensitivity * sev_factor)
            delta["distress"] = int(30 * sensitivity * sev_factor)
            delta["trust"] = -int(25 * distrust * sev_factor * rapport_dampening)
            delta["cooperation"] = -int(25 * sev_factor * rapport_dampening)
            delta["frustration"] = int(20 * sensitivity * sev_factor)

        # Alarmist / Frightening
        if analysis.get("alarmist") or intent == "alarmist" or intent == "frightening" or tone == "frightening":
            delta["fear"] = int(30 * sensitivity * fear_death_factor * sev_factor)
            delta["anxiety"] = int(25 * sensitivity * sev_factor)
            delta["distress"] = int(25 * sensitivity * sev_factor)
            delta["trust"] = -int(10 * distrust * sev_factor * rapport_dampening)
            delta["shock"] = int(40 * sensitivity * fear_death_factor * sev_factor)
            delta["frustration"] = int(10 * sensitivity * sev_factor)
            delta["hope"] = -int(15 * sev_factor)

        # Hopeless Statement
        if intent == "hopeless_statement":
            delta["fear"] = int(20 * sensitivity * fear_death_factor * sev_factor)
            delta["distress"] = int(25 * sensitivity * sev_factor)
            delta["trust"] = -int(20 * distrust * sev_factor * rapport_dampening)
            delta["hope"] = -int(25 * sev_factor)
            delta["frustration"] = int(15 * sensitivity * sev_factor)
            delta["cooperation"] = -int(10 * sev_factor)

        # Impatience
        if intent == "impatience":
            delta["frustration"] = int(20 * sensitivity * sev_factor)
            delta["trust"] = -int(10 * distrust * sev_factor * rapport_dampening)
            delta["cooperation"] = -int(10 * sev_factor * rapport_dampening)
            delta["anger"] = int(15 * sensitivity * sev_factor)

        # Apology
        if intent == "apology" or analysis.get("apology"):
            delta["trust"] = int(15 * (1.0 / max(0.4, distrust)) * sev_factor)
            delta["anger"] = -int(15 * sev_factor)
            delta["frustration"] = -int(15 * sev_factor)
            delta["distress"] = -int(8 * sev_factor)
            delta["cooperation"] = int(12 * coop_base * sev_factor)
            delta["fear"] = -int(8 * sev_factor)

        # Professional Explanation
        if intent == "professional_explanation":
            delta["confusion"] = -int(15 * sev_factor)
            delta["trust"] = int(8 * (1.0 / max(0.4, distrust)) * sev_factor)
            delta["cooperation"] = int(6 * coop_base * sev_factor)

        return delta

    def set_values(self, values: Dict[str, int]) -> None:
        """Directly set emotion values (e.g. from LLM output)."""
        for key, value in values.items():
            if hasattr(self, key):
                setattr(self, key, self._clamp(int(value)))

    def get_label(self) -> str:
        """Return a human-readable emotional state label."""
        for label, condition in EMOTION_LABEL_THRESHOLDS:
            if condition(self):
                return label
        return "Calm"

    def get_behavioral_cue(self) -> str:
        """Return a short behavioral description for UI display."""
        label = self.get_label()
        cues = {
            "Shocked": "The patient stares wide-eyed, visibly stunned.",
            "Frightened": "The patient looks frightened and is seeking reassurance.",
            "Distressed": "The patient appears visibly distressed.",
            "Anxious": "The patient is fidgeting and seems increasingly nervous.",
            "Concerned": "The patient looks concerned and is watching you carefully.",
            "Reassured": "The patient seems warmer and more comfortable speaking with you.",
            "Angry": "The patient appears frustrated and guarded.",
            "Confused": "The patient looks confused.",
            "Calm": "The patient appears relaxed.",
        }
        return cues.get(label, "")

    def to_dict(self) -> Dict[str, int]:
        return {
            "fear": self.fear,
            "anxiety": self.anxiety,
            "trust": self.trust,
            "confusion": self.confusion,
            "distress": self.distress,
            "hope": self.hope,
            "anger": self.anger,
            "embarrassment": self.embarrassment,
            "pain": self.pain,
            "shock": self.shock,
            "sadness": self.sadness,
            "cooperation": self.cooperation,
            "frustration": self.frustration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmotionalState":
        if not data:
            return cls()
        return cls(
            fear=int(data.get("fear", 30)),
            anxiety=int(data.get("anxiety", 35)),
            trust=int(data.get("trust", 50)),
            confusion=int(data.get("confusion", 20)),
            distress=int(data.get("distress", 25)),
            hope=int(data.get("hope", 65)),
            anger=int(data.get("anger", 10)),
            embarrassment=int(data.get("embarrassment", 10)),
            pain=int(data.get("pain", 45)),
            shock=int(data.get("shock", 0)),
            sadness=int(data.get("sadness", 10)),
            cooperation=int(data.get("cooperation", 60)),
            frustration=int(data.get("frustration", 15)),
        )

    def to_prompt_description(self) -> str:
        """Describe the current emotional state in natural language for the LLM."""
        label = self.get_label()
        parts = [f"Your current emotional state is: {label}."]

        if self.shock >= 70:
            parts.append(
                "You are in a state of profound shock — you have just heard something so alarming that "
                "you can barely process it. You feel stunned, your mind is racing, and you may struggle "
                "to find words."
            )
        if self.sadness >= 50:
            parts.append("A wave of sadness has hit you — you feel grief-stricken and heavy.")
        if self.fear >= 60:
            parts.append("You are feeling a significant amount of fear right now and may seek reassurance repeatedly.")
        if self.anxiety >= 60:
            parts.append("Your anxiety is elevated, making it sometimes hard to focus.")
        if self.trust < 35:
            parts.append("You don't trust this doctor and are highly guarded or defensive in your answers.")
        elif self.trust >= 70:
            parts.append("You feel relatively safe and trust this provider, answering openly.")
        if self.confusion >= 50:
            parts.append("You are highly confused about what is happening and should ask for clarification.")
        if self.distress >= 60:
            parts.append("You are in notable distress.")
        if self.hope >= 70:
            parts.append("You feel hopeful.")
        elif self.hope <= 20:
            parts.append("You feel hopeless.")
        if self.anger >= 50:
            parts.append("You are angry/defensive and may give shorter, sharper answers.")
        if self.pain >= 65:
            parts.append("The physical pain/discomfort is very intense right now.")
        if self.cooperation < 40:
            parts.append("You feel uncooperative and reluctant to share details easily, requiring doctor patience.")
        if self.frustration >= 50:
            parts.append("You are feeling quite frustrated and impatient with the doctor's communication style.")

        return " ".join(parts)
