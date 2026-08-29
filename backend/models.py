import datetime
from datetime import timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    specialization = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    sessions = relationship("SimulationSession", back_populates="user", cascade="all, delete-orphan")


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    duration_mins = Column(Integer, default=20)
    data = Column(JSON, nullable=False)

    sessions = relationship("SimulationSession", back_populates="case", cascade="all, delete-orphan")


class SimulationSession(Base):
    __tablename__ = "simulation_sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)

    remaining_resources = Column(Integer, default=1000)
    elapsed_seconds = Column(Integer, default=0)
    status = Column(String, default="in_progress")  # in_progress | completed

    # JSON state: [{diagnosis: str, confidence: int}]
    differential_diagnoses = Column(JSON, default=list)

    # Virtual patient agent state (emotion, memory, personality, beliefs)
    patient_agent_state = Column(JSON, nullable=True, default=None)

    # Final submission
    final_diagnosis = Column(String, nullable=True)
    immediate_priority = Column(Text, nullable=True)
    evidence_justification = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")
    case = relationship("Case", back_populates="sessions")
    actions = relationship("StudentAction", back_populates="session", cascade="all, delete-orphan")
    evaluation = relationship(
        "Evaluation", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )


class StudentAction(Base):
    __tablename__ = "student_actions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("simulation_sessions.id"), nullable=False)

    # question | examination | investigation | diagnosis_update | patient_response | system
    action_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    cost = Column(Integer, default=0)
    category = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    session = relationship("SimulationSession", back_populates="actions")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("simulation_sessions.id"), nullable=False)

    history_score = Column(Float, default=0)
    differential_score = Column(Float, default=0)
    investigation_score = Column(Float, default=0)
    evidence_interpretation_score = Column(Float, default=0)
    reasoning_score = Column(Float, default=0)
    decision_score = Column(Float, default=0)
    resource_efficiency_score = Column(Float, default=0)

    # New: Communication and patient interaction scores
    communication_score = Column(Float, default=0)
    empathy_score = Column(Float, default=0)
    patient_interaction_score = Column(Float, default=0)

    final_score = Column(Float, default=0)

    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    critical_mistakes = Column(JSON, default=list)
    summary = Column(Text, nullable=True)

    # Emotional timeline for results page
    emotional_timeline = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    session = relationship("SimulationSession", back_populates="evaluation")
