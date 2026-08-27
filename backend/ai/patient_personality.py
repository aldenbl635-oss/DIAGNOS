"""
Patient personality profile system.
Personality values are internal simulation state (0-100 scale).
They are NEVER exposed to the student.
"""
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class PersonalityProfile:
    baseline_anxiety: int = 50
    emotional_sensitivity: int = 50
    trustfulness: int = 50
    cooperativeness: int = 70
    health_literacy: int = 40
    fear_of_death: int = 60
    privacy_sensitivity: int = 40
    assertiveness: int = 50
    pain_tolerance: int = 50
    distrust_of_medical: int = 30

    def to_dict(self) -> Dict[str, int]:
        return {
            "baseline_anxiety": self.baseline_anxiety,
            "emotional_sensitivity": self.emotional_sensitivity,
            "trustfulness": self.trustfulness,
            "cooperativeness": self.cooperativeness,
            "health_literacy": self.health_literacy,
            "fear_of_death": self.fear_of_death,
            "privacy_sensitivity": self.privacy_sensitivity,
            "assertiveness": self.assertiveness,
            "pain_tolerance": self.pain_tolerance,
            "distrust_of_medical": self.distrust_of_medical,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalityProfile":
        return cls(
            baseline_anxiety=int(data.get("baseline_anxiety", 50)),
            emotional_sensitivity=int(data.get("emotional_sensitivity", 50)),
            trustfulness=int(data.get("trustfulness", 50)),
            cooperativeness=int(data.get("cooperativeness", 70)),
            health_literacy=int(data.get("health_literacy", 40)),
            fear_of_death=int(data.get("fear_of_death", 60)),
            privacy_sensitivity=int(data.get("privacy_sensitivity", 40)),
            assertiveness=int(data.get("assertiveness", 50)),
            pain_tolerance=int(data.get("pain_tolerance", 50)),
            distrust_of_medical=int(data.get("distrust_of_medical", 30)),
        )

    def to_narrative(self) -> str:
        """Convert personality to natural language description for LLM prompt."""
        parts = []

        if self.baseline_anxiety > 65:
            parts.append("You are a naturally anxious person and tend to worry about your health.")
        elif self.baseline_anxiety < 35:
            parts.append("You tend to stay calm and composed even in stressful situations.")
        else:
            parts.append("You have a moderate baseline anxiety level — you can cope but do feel nervous in unfamiliar medical situations.")

        if self.emotional_sensitivity > 65:
            parts.append("You are emotionally sensitive and pick up on subtle cues in how people speak to you.")
        elif self.emotional_sensitivity < 35:
            parts.append("You are not particularly sensitive to tone or emotional cues.")

        if self.trustfulness < 35:
            parts.append("You are naturally distrustful and take time to open up to strangers, including medical professionals.")
        elif self.trustfulness > 65:
            parts.append("You tend to trust medical professionals quickly and follow their lead.")

        if self.cooperativeness > 70:
            parts.append("You try to cooperate and answer questions as best you can.")
        elif self.cooperativeness < 40:
            parts.append("You can be reluctant to answer some questions and may be defensive at times.")

        if self.health_literacy < 35:
            parts.append("You have limited medical knowledge. Medical jargon confuses you and you often need things explained in simple terms.")
        elif self.health_literacy > 65:
            parts.append("You have reasonable health literacy and understand some medical terms from past experiences.")

        if self.fear_of_death > 70:
            parts.append("The idea of a serious illness or death frightens you deeply.")

        if self.privacy_sensitivity > 60:
            parts.append("You are somewhat private and may hesitate to share personal information unless you feel safe.")

        if self.distrust_of_medical > 60:
            parts.append("You have had mixed experiences with healthcare and may question recommendations.")

        if self.pain_tolerance < 35:
            parts.append("You have a low pain tolerance and tend to express discomfort strongly.")

        return " ".join(parts)
