"""
Patient memory system.
Stores important events from the conversation with importance weighting.
Prevents the LLM from receiving the entire raw conversation history
by providing a summarized, prioritized memory view.
"""
import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


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

    def add_event(
        self,
        event: str,
        importance: float = 0.5,
        category: str = "general"
    ) -> None:
        """Record a memory event."""
        self.events.append(MemoryEvent(event=event, importance=importance, category=category))
        # Prune if too many — remove lowest importance old events
        if len(self.events) > self.MAX_EVENTS:
            self.events.sort(key=lambda e: e.importance, reverse=True)
            self.events = self.events[:self.MAX_EVENTS]

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

        if not top:
            return "No significant memory events yet."

        lines = []
        for ev in reversed(top):  # chronological order for LLM
            lines.append(f"- {ev.event} (importance: {ev.importance:.1f})")

        return "\n".join(lines)

    def has_answered(self, topic_keyword: str) -> bool:
        """Check if the patient has already answered about a topic."""
        topic_lower = topic_keyword.lower()
        for ev in self.events:
            if ev.category == "question_answered" and topic_lower in ev.event.lower():
                return True
        return False

    def get_important_events(self, min_importance: float = 0.7) -> List[MemoryEvent]:
        return [e for e in self.events if e.importance >= min_importance]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatientMemory":
        memory = cls()
        if data and "events" in data:
            for ev_data in data["events"]:
                memory.events.append(MemoryEvent.from_dict(ev_data))
        return memory
