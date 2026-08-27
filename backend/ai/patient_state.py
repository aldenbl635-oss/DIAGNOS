"""
Patient state container — combines emotion, memory, beliefs, goals, revealed facts.
This is the full agent state persisted per simulation session.
"""
import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from ai.patient_emotion import EmotionalState
from ai.patient_memory import PatientMemory
from ai.patient_personality import PersonalityProfile


@dataclass
class PatientAgentState:
    """Full persistent state of the virtual patient agent for one session."""

    # Core state components
    emotion: EmotionalState = field(default_factory=EmotionalState)
    memory: PatientMemory = field(default_factory=PatientMemory)
    personality: PersonalityProfile = field(default_factory=PersonalityProfile)

    # Belief system — can drift based on conversation
    beliefs: List[str] = field(default_factory=list)

    # Goals — stable throughout session
    goals: List[str] = field(default_factory=list)

    # Track what factual topics have been revealed in conversation
    revealed_facts: List[str] = field(default_factory=list)

    # Communication history (student style labels)
    communication_history: List[str] = field(default_factory=list)

    # Session metadata
    turn_count: int = 0
    simulation_phase: str = "initial"  # initial | history | investigation | discussion | closing

    # Emotional event log for timeline reconstruction
    emotional_events: List[Dict[str, Any]] = field(default_factory=list)

    def add_emotional_event(self, description: str, emotion_label: str, turn: int) -> None:
        """Record a notable emotional event for timeline display."""
        self.emotional_events.append({
            "description": description,
            "emotion_label": emotion_label,
            "turn": turn,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })

    def add_communication_event(self, style: str) -> None:
        """Record how the student communicated in this turn."""
        self.communication_history.append(style)

    def advance_phase(self) -> None:
        """Advance simulation phase based on turn count and revealed facts."""
        self.turn_count += 1
        if self.turn_count <= 3:
            self.simulation_phase = "initial"
        elif self.turn_count <= 10:
            self.simulation_phase = "history"
        elif len(self.revealed_facts) >= 5:
            self.simulation_phase = "investigation"
        else:
            self.simulation_phase = "history"

    def mark_fact_revealed(self, fact_key: str) -> None:
        if fact_key not in self.revealed_facts:
            self.revealed_facts.append(fact_key)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emotion": self.emotion.to_dict(),
            "memory": self.memory.to_dict(),
            "personality": self.personality.to_dict(),
            "beliefs": self.beliefs,
            "goals": self.goals,
            "revealed_facts": self.revealed_facts,
            "communication_history": self.communication_history,
            "turn_count": self.turn_count,
            "simulation_phase": self.simulation_phase,
            "emotional_events": self.emotional_events,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], case_data: Dict[str, Any] = None) -> "PatientAgentState":
        """Reconstruct state from persisted dict. Merges case defaults if provided."""
        if not data:
            state = cls()
            if case_data:
                state._apply_case_defaults(case_data)
            return state

        emotion = EmotionalState.from_dict(data.get("emotion", {}))
        memory = PatientMemory.from_dict(data.get("memory", {}))
        personality = PersonalityProfile.from_dict(data.get("personality", {}))

        state = cls(
            emotion=emotion,
            memory=memory,
            personality=personality,
            beliefs=data.get("beliefs", []),
            goals=data.get("goals", []),
            revealed_facts=data.get("revealed_facts", []),
            communication_history=data.get("communication_history", []),
            turn_count=data.get("turn_count", 0),
            simulation_phase=data.get("simulation_phase", "initial"),
            emotional_events=data.get("emotional_events", []),
        )

        return state

    def _apply_case_defaults(self, case_data: Dict[str, Any]) -> None:
        """Initialize from case JSON configuration."""
        personality_data = case_data.get("patient_personality", {})
        if personality_data:
            self.personality = PersonalityProfile.from_dict(personality_data)

        # Initialize emotion from personality baseline
        self.emotion.anxiety = min(100, self.personality.baseline_anxiety + 10)
        self.emotion.fear = max(0, self.personality.baseline_anxiety - 15)
        self.emotion.trust = max(20, 100 - self.personality.distrust_of_medical - 10)

        self.beliefs = list(case_data.get("patient_beliefs", []))
        self.goals = list(case_data.get("patient_goals", []))

    @classmethod
    def initialize_from_case(cls, case_data: Dict[str, Any]) -> "PatientAgentState":
        """Create a fresh state from case configuration."""
        state = cls()
        state._apply_case_defaults(case_data)
        return state
