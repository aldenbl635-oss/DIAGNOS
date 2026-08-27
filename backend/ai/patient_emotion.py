"""
Emotional state engine for the virtual patient.
All values are on a 0-100 scale (internal simulation state).
These values are NEVER directly exposed to the student.
The student only sees a derived human-readable label and behavioral cues.
"""
from dataclasses import dataclass, field
from typing import Dict, Any


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
    shock: int = 0    # acute shock / disbelief (spiked by sudden alarming statements)
    sadness: int = 10  # grief / emotional heaviness

    def _clamp(self, value: int) -> int:
        return max(0, min(100, value))

    def apply_update(self, delta: Dict[str, int]) -> None:
        """Apply a delta dict of {emotion: delta_value} to current state."""
        for key, change in delta.items():
            if hasattr(self, key):
                current = getattr(self, key)
                setattr(self, key, self._clamp(current + change))

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
        )

    def to_prompt_description(self) -> str:
        """Describe the current emotional state in natural language for the LLM."""
        label = self.get_label()
        parts = [f"Your current emotional state is: {label}."]

        if self.shock >= 70:
            parts.append(
                "You are in a state of profound shock — you have just heard something so alarming that "
                "you can barely process it. You feel stunned, your mind is racing, and you may struggle "
                "to find words. Your initial reaction is raw disbelief mixed with terror."
            )
        if self.sadness >= 50:
            parts.append("A wave of sadness has hit you — you feel grief-stricken and heavy with worry.")
        if self.fear >= 60:
            parts.append("You are feeling a significant amount of fear right now.")
        if self.anxiety >= 60:
            parts.append("Your anxiety is elevated.")
        if self.trust < 35:
            parts.append("You don't fully trust this person yet and may be guarded.")
        elif self.trust >= 70:
            parts.append("You feel relatively safe and trust this person.")
        if self.confusion >= 50:
            parts.append("You are confused about what is happening.")
        if self.distress >= 60:
            parts.append("You are in notable distress.")
        if self.hope >= 70:
            parts.append("You feel hopeful that things will be okay.")
        elif self.hope <= 20:
            parts.append("You feel like hope is slipping away from you.")
        if self.anger >= 50:
            parts.append("You are feeling frustrated or angry.")
        if self.pain >= 65:
            parts.append("The physical discomfort is quite significant right now.")

        return " ".join(parts)
