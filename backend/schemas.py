from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

# Auth schemas
class UserRegister(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)
    specialization: str = Field(..., description="Student's medical specialization")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    specialization: Optional[str] = None
    created_at: datetime
    
class UserUpdateSpecialization(BaseModel):
    specialization: str = Field(..., description="Student's medical specialization")

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class TokenData(BaseModel):
    email: Optional[str] = None

# Case schemas
class CaseBriefOut(BaseModel):
    id: str
    title: str
    specialty: str
    difficulty: str
    duration_mins: int
    patient_age: int
    patient_sex: str
    chief_complaint: str

class PatientVitalsOut(BaseModel):
    bp: str
    hr: str
    spo2: str
    temp: str

class ExaminationBriefOut(BaseModel):
    type: str
    name: str

class InvestigationBriefOut(BaseModel):
    id: str
    name: str
    cost: int
    category: str

class CaseDetailOut(CaseBriefOut):
    patient_name: str
    vitals: PatientVitalsOut
    examinations: List[ExaminationBriefOut]
    investigations: List[InvestigationBriefOut]
    differential_options: List[str] = []
    initial_briefing: Optional[str] = None

# Simulation schemas
class SimulationStart(BaseModel):
    case_id: str

class SimulationSessionOut(BaseModel):
    id: str
    case_id: str
    remaining_resources: int
    elapsed_seconds: int
    status: str
    differential_diagnoses: List[Dict[str, Any]]
    final_diagnosis: Optional[str] = None
    immediate_priority: Optional[str] = None
    evidence_justification: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class QuestionSubmit(BaseModel):
    question: str = Field(..., min_length=2)

class QuestionResponse(BaseModel):
    answer: str
    category: str
    remaining_resources: int
    elapsed_seconds: int
    emotion_label: Optional[str] = None
    emotional_cue: Optional[str] = None
    communication_state: Optional[str] = None
    vitals: Optional[PatientVitalsOut] = None

class ExamSubmit(BaseModel):
    examination_type: str # e.g. general, cardiovascular, respiratory, etc.

class ExamResponse(BaseModel):
    result: str
    remaining_resources: int
    elapsed_seconds: int
    patient_reaction: Optional[str] = None

class InvestigationSubmit(BaseModel):
    investigation_id: str

class InvestigationResponse(BaseModel):
    investigation_id: str
    name: str
    cost: int
    result: str
    interpretation: str
    remaining_resources: int
    elapsed_seconds: int
    patient_reaction: Optional[str] = None

class DiagnosisUpdateSubmit(BaseModel):
    # e.g., [{"diagnosis": "Acute Coronary Syndrome", "confidence": 60}]
    differential_diagnoses: List[Dict[str, Any]] 

class FinalDiagnosisSubmit(BaseModel):
    final_diagnosis: str
    immediate_priority: str
    evidence_justification: str

# Evaluation & dashboard schemas
class ChatMessageOut(BaseModel):
    role: str
    text: str
    category: Optional[str] = None
    emotion_label: Optional[str] = None
    emotional_cue: Optional[str] = None
    communication_state: Optional[str] = None

class InvestigationStateOut(BaseModel):
    name: str
    cost: int
    result: str
    interpretation: str

class SimulationSessionDetailOut(BaseModel):
    session: SimulationSessionOut
    case: CaseDetailOut
    actions: List["ActionOut"]
    chat_messages: List[ChatMessageOut]
    exams_revealed: Dict[str, str]
    investigations_ordered: Dict[str, InvestigationStateOut]

class EvaluationOut(BaseModel):
    id: int
    session_id: str
    history_score: float
    differential_score: float = 0.0
    investigation_score: float
    evidence_interpretation_score: float
    reasoning_score: float
    decision_score: float
    resource_efficiency_score: float
    final_score: float
    strengths: List[str]
    weaknesses: List[str]
    critical_mistakes: List[str]
    summary: str
    created_at: datetime
    
    # New: Communication and patient interaction scores
    communication_score: float = 0.0
    empathy_score: float = 0.0
    patient_interaction_score: float = 0.0
    emotional_timeline: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)

class ActionOut(BaseModel):
    action_type: str
    content: str
    cost: int
    category: Optional[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class SimulationResultOut(BaseModel):
    session: SimulationSessionOut
    evaluation: EvaluationOut
    actions: List[ActionOut]

class DashboardStatsOut(BaseModel):
    cases_completed: int
    average_score: float
    best_score: float
    streak: int
    recent_simulations: List[Dict[str, Any]]
    category_scores: Dict[str, float]
    recommendation: Optional[str] = None
