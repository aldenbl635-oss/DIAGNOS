"""
Patient memory system.
Stores important events from the conversation with importance weighting.
Prevents the LLM from receiving the entire raw conversation history
by providing a summarized, prioritized memory view.
"""
import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Union, Set

@dataclass
class MemoryEvent:
    event: str
    importance: float  # 0.0 - 1.0
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    category: str = "general"  # general | question_answered | emotional | clinical | student_behavior

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEvent":
        return cls(
            event=data.get("event", ""),
            importance=float(data.get("importance", 0.5)),
            timestamp=data.get("timestamp", datetime.datetime.utcnow().isoformat()),
            category=data.get("category", "general"),
        )


class PatientMemory:
    MAX_EVENTS = 40  # Absolute maximum stored
    MAX_PROMPT_EVENTS = 12  # Max sent to LLM

    def __init__(self):
        self.events: List[MemoryEvent] = []
        
        # PART 11 - Persisted encounter memory
        self.short_term_memory: List[Dict[str, str]] = []  # List of recent raw turned messages (role/text)
        self.important_events: List[MemoryEvent] = []     # High importance events
        self.medical_information_revealed: Set[str] = set() # Set of categories (e.g. pain_characteristics)
        self.emotional_events: List[str] = []             # Reassurance, apologies, alarmist remarks
        self.trust_events: List[str] = []                 # Insults, threats, nice comments
        self.unanswered_patient_questions: List[str] = [] # Questions the patient asked but student hasn't addressed

    def add_event(
        self,
        event: str,
        importance: float = 0.5,
        category: str = "general"
    ) -> None:
        """Record a memory event."""
        m_event = MemoryEvent(event=event, importance=importance, category=category)
        self.events.append(m_event)
        
        # Classify into specific sub-registers
        if importance >= 0.7:
            self.important_events.append(m_event)
            
        if category == "clinical" or category == "question_answered":
            # Extract keywords or record generally
            self.medical_information_revealed.add(event)
            
        if category == "emotional":
            self.emotional_events.append(event)
            
        if category == "student_behavior":
            self.trust_events.append(event)

        # Prune if too many — remove lowest importance old events from main register
        if len(self.events) > self.MAX_EVENTS:
            self.events.sort(key=lambda e: e.importance, reverse=True)
            self.events = self.events[:self.MAX_EVENTS]

    def add_turn(self, role: str, text: str) -> None:
        """Record recent utterances in short-term conversation logs."""
        self.short_term_memory.append({"role": role, "text": text})
        # Keep only latest 10 turns
        if len(self.short_term_memory) > 10:
            self.short_term_memory.pop(0)

    def get_answered_topics(self) -> List[str]:
        """Return list of topics/questions the patient has already answered."""
        return [
            e.event for e in self.events
            if e.category == "question_answered"
        ]

    def get_relevant_summary(self, max_events: int = None) -> str:
        """Get prioritized memory summary for LLM context."""
        limit = max_events or self.MAX_PROMPT_EVENTS
        # Sort by importance descending, then by recency (recent high-importance first)
        sorted_events = sorted(self.events, key=lambda e: (e.importance, e.timestamp), reverse=True)
        top = sorted_events[:limit]

        lines = []
        
        # Add a section highlighting what the doctor has previously commented on/agreed
        if self.trust_events:
            lines.append("Important actions/threats/statements:")
            for te in self.trust_events[-3:]:
                lines.append(f"- {te}")
                
        if self.emotional_events:
            lines.append("Important emotional moments:")
            for ee in self.emotional_events[-3:]:
                lines.append(f"- {ee}")

        if not top and not lines:
            return "No significant memory events yet."

        lines.append("General memory items:")
        for ev in reversed(top):  # chronological order for LLM
            lines.append(f"- {ev.event} (importance: {ev.importance:.1f})")

        return "\n".join(lines)

    def has_answered(self, topic_keyword: str) -> bool:
        """Check if the patient has already answered about a topic."""
        topic_lower = topic_keyword.lower()
        for ev in self.events:
            if ev.category == "question_answered" and topic_lower in ev.event.lower():
                return True
        for fact in self.medical_information_revealed:
            if topic_lower in fact.lower():
                return True
        return False

    def get_important_events(self, min_importance: float = 0.7) -> List[MemoryEvent]:
        return [e for e in self.events if e.importance >= min_importance]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "short_term_memory": self.short_term_memory,
            "important_events": [e.to_dict() for e in self.important_events],
            "medical_information_revealed": list(self.medical_information_revealed),
            "emotional_events": self.emotional_events,
            "trust_events": self.trust_events,
            "unanswered_patient_questions": self.unanswered_patient_questions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatientMemory":
        memory = cls()
        if not data:
            return memory
            
        if "events" in data:
            for ev_data in data["events"]:
                memory.events.append(MemoryEvent.from_dict(ev_data))
                
        memory.short_term_memory = data.get("short_term_memory", [])
        
        if "important_events" in data:
            memory.important_events = [MemoryEvent.from_dict(ed) for ed in data["important_events"]]
            
        memory.medical_information_revealed = set(data.get("medical_information_revealed", []))
        memory.emotional_events = data.get("emotional_events", [])
        memory.trust_events = data.get("trust_events", [])
        memory.unanswered_patient_questions = data.get("unanswered_patient_questions", [])
        
        return memory
