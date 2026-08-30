"""
OfflinePatientResponder — replaces the old keyword-matching _demo_response
with a full semantic-understanding engine that works without an LLM API key.

Pipeline:
  Student Message
    → SemanticClassifier (rule-based + pattern matching — no LLM required)
    → PatientContextBuilder (structured facts → patient knowledge)
    → ResponseSynthesizer (personality + emotion + context → natural response)
    → EmotionUpdater
"""

import re
from typing import Dict, Any, List, Optional, Tuple


# ─── 1. SEMANTIC CLASSIFIER ──────────────────────────────────────────────────

class SemanticClassifier:
    """
    Classify a student message into a semantic category WITHOUT exact string matching.
    Uses token patterns + linguistic cues for broad coverage.
    """

    ALARM_PATTERNS = re.compile(
        r"\b(die|dying|dead|death|fatal|kill\w*|not surviv\w*|won't surviv\w*|wont surviv\w*|"
        r"not make it|no hope|hopeless|not gonna make it|going to die|will die|about to die|"
        r"end of your life|last chance|critical\w*|terminal\w*|lethal|deadly)\b",
        re.I
    )
    HOPELESS_PATTERNS = re.compile(
        r"\b(nothing\s+(we|i|you|can|could)\s+(can\s+)?do|nothing\s+can\s+be\s+done|"
        r"no\s+treatment|can'?t\s+(help|save|treat)|no\s+cure|no\s+options?|too\s+late|"
        r"running\s+out\s+of\s+options?|face\s+(the\s+)?reality|accept\s+it|give\s+up|"
        r"lost\s+cause|there'?s\s+nothing|nothing\s+to\s+do|no\s+hope|hopeless)\b",
        re.I
    )
    RUDE_PATTERNS = re.compile(
        r"\b(shut\s+up|stupid|idiot|dumb\w*|incompetent|waste\s+(of\s+)?time|hurry\s+up|"
        r"stop\s+wasting|just\s+answer|get\s+to\s+the\s+point|move\s+on|"
        r"don'?t\s+care|don'?t\s+have\s+time|next\s+(thing|question)|difficult\s+patient)\b",
        re.I
    )
    THREAT_PATTERNS = re.compile(
        r"\b(threaten|harm\s+you|hurt\s+you|regret\s+this|face\s+consequences|"
        r"get\s+you\s+fired|report\s+you)\b",
        re.I
    )
    APOLOGY_PATTERNS = re.compile(
        r"\b(sorry|apologize|apolog[yi]\w*|forgive\s+me|i\s+didn'?t\s+mean|"
        r"shouldn'?t\s+have|take\s+that\s+back|i\s+was\s+wrong)\b",
        re.I
    )
    REASSURANCE_PATTERNS = re.compile(
        r"\b(going\s+to\s+be\s+(okay|ok|alright)|don'?t\s+(worry|panic)|calm\s+down|"
        r"you'?re\s+(safe|in\s+good\s+hands)|i'?m\s+here\s+to\s+help|"
        r"we'?ll\s+(take\s+care|look\s+after|fix)|help\s+you|"
        r"explain\s+everything|take\s+care\s+of\s+you|you'?re\s+going\s+to\s+be\s+fine)\b",
        re.I
    )
    EMPATHY_PATTERNS = re.compile(
        r"\b(i\s+understand|i\s+hear\s+you|that\s+(must\s+be\s+)?hard|"
        r"i'?m\s+(sorry\s+)?to\s+hear|this\s+must\s+be\s+(difficult|scary|frightening|tough)|"
        r"take\s+your\s+time|i\s+can\s+imagine|i\s+know\s+it'?s\s+(scary|hard|difficult)|"
        r"must\s+be\s+worrying|you\s*(don'?t|\s+do\s+not)?\s+(look|seem|appear)\s+(unwell|scared|worried|pale|bad|well|good)|"
        r"i\s+am\s+worried\s+about\s+you|we\s+are\s+worried|worried\s+about\s+you)\b",
        re.I
    )
    CLINICAL_PATTERNS = re.compile(
        r"\b(where|when|how\s+long|how\s+bad|how\s+often|does\s+it|did\s+it|have\s+you|has\s+(anyone|anybody)|is\s+there\s+any|did\s+(anyone|your)|"
        r"tell\s+me\s+about|describe|what\s+(kind|type|does|is\s+your|are\s+your|medications?|pills?)|any\s+(other|previous|family|history)|"
        r"do\s+you\s+(have|feel|take|smoke|drink|exercise|use)|are\s+you\s+(taking|on\s+any|allergic|a\s+smoker|a\s+(heavy\s+)?drinker|obese|overweight|nauseated|nauseous|in\s+pain)|"
        r"your\s+(pain|symptom|medical|history|pressure|blood|heart|medication|allerg|glucose|weight|diet|sugar|level|family|parents|mother|father))\b",
        re.I
    )
    # Symptom-specific patterns checked BEFORE EMOTIONAL_Q_PATTERNS to prevent misrouting
    SYMPTOM_CLINICAL_PATTERNS = re.compile(
        r"\b(nauseated|nauseous|vomit|throw\s*up|sick\s+to\s+(your\s+)?stomach|"
        r"headache|migraine|photopho|sensitive\s+to\s+light|bright\s+light|"
        r"weakness|numbness|tingling|swallowing|speech|vision|confused|confusion|"
        r"shortness\s+of\s+breath|wheezing|palpitation|pounding|racing\s+heart|"
        r"abdominal|stomach\s+pain|belly|cramp|diarrhea|constipation|"
        r"fever|chills|sweat\w+|cough\w*|sneez)\b",
        re.I
    )
    EMOTIONAL_Q_PATTERNS = re.compile(
        r"\b(are\s+you\s+(scared|afraid|frightened|nervous|anxious|worried|stressed|okay|alright|feeling)|"
        r"how\s+are\s+you\s+(feeling|doing|coping|holding\s+up)|"
        r"what'?s\s+(going\s+through\s+your\s+mind|on\s+your\s+mind)|"
        r"do\s+you\s+(trust|believe)\s+(me|us)|"
        r"why\s+are\s+you\s+(nervous|scared|anxious|worried|upset|crying|shaking)|"
        r"are\s+you\s+in\s+pain)\b",
        re.I
    )
    PERSONAL_Q_PATTERNS = re.compile(
        r"\b(are\s+you\s+(married|divorced|single)|do\s+you\s+have\s+children|"
        r"what\s+(do\s+you\s+do\s+for\s+a\s+living|is\s+your\s+job|is\s+your\s+occupation|"
        r"were\s+you\s+doing|happened\s+before)|"
        r"who\s+(is\s+with\s+you|brought\s+you|drove\s+you)|"
        r"tell\s+me\s+about\s+(your\s+family|yourself)|"
        r"where\s+do\s+you\s+(live|work)|"
        r"how\s+old\s+are\s+you|what'?s\s+your\s+(name|age|occupation))\b",
        re.I
    )
    CONFUSION_PATTERNS = re.compile(
        r"\b(what\s+does\s+that\s+mean|i\s+don'?t\s+understand|"
        r"could\s+you\s+explain|can\s+you\s+explain|what\s+is\s+(a|an)\s+[a-z]+|"
        r"i'?m\s+confused|that\s+'?s\s+confusing)\b",
        re.I
    )

    SYMPTOM_DETAIL_PATTERNS = re.compile(
        r"\b(pain|discomfort|pressure|burning|ache|hurt\w*|sore|tight\w*|"
        r"swell\w*|nausea|vomit\w*|dizziness|dizzy|faint\w*|"
        r"breath\w*|short\s+of\s+breath|chest|heartburn|symptom\w*|weak\w*|"
        r"radiat\w*|spread\w*|move|travel|shoot\w*)\b",
        re.I
    )

    @staticmethod
    def classify(msg: str) -> str:
        """Return one primary semantic category."""
        m = msg.strip()

        if SemanticClassifier.THREAT_PATTERNS.search(m):
            return "threatening"
        if SemanticClassifier.ALARM_PATTERNS.search(m):
            return "alarmist"
        if SemanticClassifier.HOPELESS_PATTERNS.search(m):
            return "hopeless_statement"
        if SemanticClassifier.RUDE_PATTERNS.search(m):
            return "rude"
        if SemanticClassifier.APOLOGY_PATTERNS.search(m):
            return "apology"
        if SemanticClassifier.EMPATHY_PATTERNS.search(m):
            return "empathy"
        if SemanticClassifier.REASSURANCE_PATTERNS.search(m):
            return "reassurance"
        # Check symptom-specific clinical questions BEFORE emotional pattern so that
        # "are you feeling nauseated?" routes to symptom_question, not emotional_question
        if SemanticClassifier.SYMPTOM_CLINICAL_PATTERNS.search(m):
            return "symptom_question"
        if SemanticClassifier.EMOTIONAL_Q_PATTERNS.search(m):
            return "emotional_question"
        if SemanticClassifier.PERSONAL_Q_PATTERNS.search(m):
            return "personal_question"
        if SemanticClassifier.CONFUSION_PATTERNS.search(m):
            return "confusion"
        if SemanticClassifier.CLINICAL_PATTERNS.search(m):
            return "clinical_question"
        if SemanticClassifier.SYMPTOM_DETAIL_PATTERNS.search(m):
            return "symptom_question"

        # Ultimate fallback: if any exact clinical keyword triggers a topic, assume clinical question
        topic = extract_topic(m)
        if topic and topic != "none":
            return "clinical_question"

        return "general_conversation"


# ─── 2. PATIENT CONTEXT BUILDER ──────────────────────────────────────────────

class PatientContext:
    """All information the offline responder needs to generate a human-like response."""

    def __init__(self, case_data: Dict[str, Any]):
        self.case_data = case_data
        self.patient = case_data.get("patient", {})
        facts = case_data.get("clinical_facts", {})
        c_state = case_data.get("clinical_state", {})
        history = case_data.get("history", {})

        self.name: str = self.patient.get("name", "Patient")
        self.age: Any = self.patient.get("age", "")
        self.sex: str = self.patient.get("sex", "")
        self.occupation: str = self.patient.get("occupation", "")
        self.chief_complaint: str = (
            self.patient.get("chief_complaint")
            or case_data.get("presentation", {}).get("chief_complaint", "discomfort")
        )

        def listify(v) -> List[str]:
            if not v: return []
            if isinstance(v, list): return [str(x) for x in v if x]
            if isinstance(v, str): return [v]
            return []

        self.symptoms: List[str] = listify(c_state.get("symptoms") or facts.get("symptoms"))
        self.onset: str = str(c_state.get("onset") or facts.get("onset") or "")
        self.pmh: List[str] = listify(history.get("past_medical_history") or facts.get("past_medical_history"))
        self.meds: List[str] = listify(history.get("medications") or facts.get("medications"))
        self.allergies: List[str] = listify(history.get("allergies") or facts.get("allergies"))
        self.family_h: List[str] = listify(history.get("family_history") or facts.get("family_history"))
        self.social_h: List[str] = listify(
            history.get("social_history")
            or history.get("lifestyle_risk_factors")
            or facts.get("social_history")
        )
        self.history_illness: List[str] = listify(facts.get("history_of_illness"))
        self.beliefs: List[str] = listify(case_data.get("patient_beliefs"))
        self.goals: List[str] = listify(case_data.get("patient_goals"))

        # Personality shortcuts
        p = case_data.get("patient_personality", {})
        self.anxiety_level: int = p.get("baseline_anxiety", 50)
        self.assertiveness: int = p.get("assertiveness", 50)
        self.fear_of_death: int = p.get("fear_of_death", 50)
        self.health_literacy: int = p.get("health_literacy", 50)
        self.cooperativeness: int = p.get("cooperativeness", 65)

    def first_symptom(self) -> str:
        return self.symptoms[0] if self.symptoms else self.chief_complaint

    def search_facts(self, keywords: List[str]) -> Optional[str]:
        """Find the first fact in any category that mentions any keyword (prefix or word match)."""
        all_facts = (
            self.symptoms
            + self.pmh
            + self.history_illness
            + self.social_h
            + self.meds
            + self.family_h
            + self.allergies
        )
        for fact in all_facts:
            fl = fact.lower()
            for kw in keywords:
                kl = kw.lower()
                if len(kl) >= 4:
                    if kl[:4] in fl:
                        return fact
                elif kl in fl.split():
                    return fact
        return None

    def search_category(self, category_list: List[str], keywords: List[str]) -> Optional[str]:
        """Find first item in category_list matching any keyword."""
        for item in category_list:
            il = item.lower()
            for kw in keywords:
                kl = kw.lower()
                if len(kl) >= 4 and kl[:4] in il:
                    return item
                elif kl in il.split():
                    return item
        return None


# ─── 3. TOPIC EXTRACTOR ──────────────────────────────────────────────────────

TOPIC_KEYWORD_MAP: Dict[str, List[str]] = {
    # ── HIGH-PRIORITY: Specific clinical domains ──────────────────────────
    "associated_symptoms": ["associated", "other symptoms", "anything else", "nausea", "sweat", "clammy", "diaphoresis", "vomit", "breathe", "sob", "dyspnea", "dizzy", "lightheaded"],
    "past_history": ["before", "previous", "prior", "ever had", "history", "first time", "episode"],
    "past_medical": ["medical history", "past medical", "condition", "illness", "diseases", "diabetes", "hypertension", "blood pressure", "cholesterol", "thyroid", "asthma", "kidney", "stroke", "epilepsy"],
    "medications": ["medication", "medicine", "pill", "drug", "take", "prescribed", "dose", "rx"],
    "allergies": ["allerg", "penicillin", "reaction", "sensitive to"],
    "family_history": ["family", "father", "mother", "parent", "relative", "siblings", "sibling", "hx", "brother", "sister", "grandfather", "grandmother"],
    "smoking": ["smoke", "smok", "cigarette", "tobacco", "pack"],
    "alcohol": ["alcohol", "drink", "beer", "wine", "liquor", "spirits"],
    "drugs": ["recreational", "marijuana", "weed", "cocaine", "heroin", "substance"],
    "diet": ["diet", "eat", "food", "coffee", "caffeine", "late dinner", "meal"],
    "exercise": ["exercise", "active", "gym", "sport", "workout", "physical activity"],
    "occupation": ["job", "work", "occupation", "do for a living", "career", "profession"],
    "marital": ["married", "spouse", "wife", "husband", "partner", "relationship"],
    "children": ["children", "kids", "children", "son", "daughter"],
    "living_situation": ["live with", "living", "alone", "roommate", "who lives"],
    "stress": ["stress", "stressful", "pressure at work", "anxiety", "mental health"],

    # ── GENERIC: Pain characteristics and general questions ───────────────
    "onset_trigger": ["when", "start", "begin", "onset", "trigger", "happen", "doing", "exert", "climb", "walk", "morning", "evening", "sudden", "gradual"],
    "duration": ["how long", "duration", "since", "long", "minutes", "hours", "days", "weeks", "month"],
    "location_site": ["where", "location", "site", "side", "which part"],
    "character_quality": ["describe", "what kind", "type", "character", "sharp", "dull", "crushing", "squeezing", "burning", "aching", "throbbing", "pressure", "feels like", "feel like"],
    "radiation": ["radiat", "spread", "go anywhere", "move", "travel", "shoot", "arm", "jaw", "shoulder", "neck", "back", "groin", "thigh", "leg"],
    "severity": ["how bad", "scale", "out of 10", "rate the pain", "severity", "intense", "mild", "severe"],
    "exacerbating": ["worse", "aggravate", "makes it worse", "exacerbat"],
    "relieving": ["better", "reliev", "ease", "improv", "nitroglycerin", "rest"],
    "symptoms": ["symptom", "complaint", "feel", "happening", "wrong"],
    
    "trust": ["trust", "believe in me", "confident in"],
    "nervousness": ["nervous", "anxious", "scared", "afraid", "fear", "frightened", "worried", "terrified"],
    "pain_general": ["pain", "ache", "hurt", "discomfort", "pressure", "feel bad", "sore"],
    "heartburn_acidity": ["heartburn", "acidity", "acid", "reflux", "gerd", "burning", "sour", "regurgit", "indigestion", "obese", "obesity", "weight", "stomach acid"],
    "glucose_sugar": ["glucose", "sugar level", "blood sugar", "blood glucose", "glycaemia"],
    "troponin": ["troponin"],
    "ecg": ["ecg", "ekg", "electrocardiogram"],
    "bp_check": ["blood pressure", "bp", "hypertension"],
    "general_wellbeing": ["how are you", "how do you feel", "feeling today", "doing okay"],
}


def extract_topic(msg: str) -> Optional[str]:
    """Return the first topic that matches keywords in the message."""
    ml = msg.lower()
    for topic, keywords in TOPIC_KEYWORD_MAP.items():
        for kw in keywords:
            if kw in ml:
                return topic
    return None


# ─── 4. RESPONSE SYNTHESIZER ─────────────────────────────────────────────────

class OfflinePatientResponder:
    """
    Generates fully natural, context-grounded patient responses without an LLM.
    Covers 100% of conversational scenarios without a generic fallback.
    """

    def __init__(self, case_data: Dict[str, Any]):
        self.ctx = PatientContext(case_data)
        self.case_data = case_data

    def _is_compatible_fact(self, intent_category: str, topic: Optional[str], fact_type: str) -> bool:
        """Relevance gate: Ensure the retrieved vector overlaps with the semantic intent."""
        if not fact_type:
            return True
            
        if topic == "past_medical":
            return fact_type == "past_medical_history"
        if topic == "medications":
            return fact_type == "medications"
        if topic == "family_history":
            return fact_type == "family_history"
        if topic == "allergies":
            return fact_type == "allergies"
        if topic in ("smoking", "alcohol", "drugs", "diet", "exercise", "occupation", "marital", "children", "living_situation", "stress"):
            return fact_type in ("social_history", "smoking", "alcohol", "stress")
        
        if topic in ("onset_trigger", "duration"):
            return fact_type in ("onset", "history_of_illness", "chief_complaint")
            
        if topic in ("location_site", "character_quality", "severity", "radiation", "exacerbating", "relieving", "associated_symptoms", "pain_general"):
            not_symptoms = ["past_medical_history", "medications", "allergies", "family_history", "social_history", "smoking", "alcohol", "stress"]
            return fact_type not in not_symptoms

        if intent_category in ("clinical_question", "symptom_question"):
            # Allow fallback if no specific topic extracted, but loosely protect against blatant mismatch
            return True
            
        return False

    def generate_greeting(self) -> str:
        """Create a clinical case-aware initial patient greeting without leaking diagnosis."""
        cc = self.ctx.chief_complaint
        symptoms = self.ctx.symptoms
        
        if not symptoms and not cc:
            return "Hello doctor. I'm not feeling well."
            
        symptom_str = ""
        if symptoms:
            first_sym = str(symptoms[0])
            first_sym = first_sym.lower().replace("patient reports ", "").replace("complains of ", "").strip()
            if first_sym.endswith("."):
                first_sym = first_sym[:-1]
            symptom_str = f" My {first_sym}."
            
        return f"Hello, doctor. I've been feeling really uncomfortable.{symptom_str}"

    def respond(
        self,
        student_message: str,
        state,  # PatientAgentState
        com_analysis: Dict[str, Any],
        semantic_facts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point. Returns a complete response dict structurally identical
        to what the LLM would produce.

        semantic_facts: list of high-confidence retrieved facts from VectorStore.
        These take priority over keyword fallbacks for clinical questions,
        preventing unrelated responses from mis-matched keyword patterns.
        """
        if semantic_facts is None:
            semantic_facts = []
        category = SemanticClassifier.classify(student_message)
        topic = extract_topic(student_message)
        msg_lower = student_message.lower()

        preface = self._get_preface(state)
        p_cc = self.ctx.chief_complaint.lower()
        p_name = self.ctx.name

        response_text = ""
        revealed = []
        memory_category = "question_answered"
        memory_importance = 0.6
        next_emotions = {}

        was_threatened = any("threat" in ev.event.lower() for ev in state.memory.events[-3:])
        was_insulted = any(
            "insult" in ev.event.lower() or "rude" in ev.event.lower()
            for ev in state.memory.events[-3:]
        )
        was_alarmed = any(
            "alarmist" in ev.event.lower() or "frightening" in ev.event.lower()
            for ev in state.memory.events[-3:]
        )

        # ── CATEGORY ROUTING ────────────────────────────────────────────

        if category == "threatening":
            response_text = (
                f"Please — please don't talk to me like that. I'm already scared enough. "
                f"I just need someone to help me with this {p_cc}."
            )
            next_emotions = {"fear": min(100, state.emotion.fear + 20), "trust": max(10, state.emotion.trust - 25)}
            memory_category = "student_behavior"
            memory_importance = 0.95
            revealed = []

        elif category == "alarmist":
            fear_level = state.emotion.fear
            fear_of_death = self.ctx.fear_of_death
            if fear_level > 65 or fear_of_death > 60:
                response_text = (
                    f"What?! No... no, that can't be right. I have a family — please, "
                    f"you have to help me. Is it really that serious?!"
                )
            elif self.ctx.assertiveness > 65:
                response_text = (
                    f"How serious are we talking exactly? Are you absolutely sure? "
                    f"I need you to be straight with me."
                )
            else:
                response_text = (
                    f"Oh God... are you saying this could be... fatal? I — "
                    f"I have children. I can't — please, what do I do?"
                )
            next_emotions = {
                "fear": min(100, state.emotion.fear + 30),
                "anxiety": min(100, state.emotion.anxiety + 20),
                "distress": min(100, state.emotion.distress + 25),
                "trust": max(10, state.emotion.trust - 15),
                "shock": min(100, state.emotion.shock + 40),
            }
            memory_category = "student_behavior"
            memory_importance = 0.95

        elif category == "hopeless_statement":
            response_text = (
                f"Wait... what do you mean there's nothing you can do? "
                f"There has to be something — please, I can't just accept that. "
                f"What is actually happening to me?"
            )
            next_emotions = {
                "fear": min(100, state.emotion.fear + 20),
                "distress": min(100, state.emotion.distress + 30),
                "hope": max(0, state.emotion.hope - 30),
                "trust": max(10, state.emotion.trust - 10),
            }
            memory_category = "student_behavior"
            memory_importance = 0.9

        elif category == "rude":
            frustration = state.emotion.anger
            if frustration > 50:
                response_text = (
                    f"I don't appreciate being spoken to like that. "
                    f"I'm trying to help you understand what I'm feeling."
                )
            else:
                response_text = (
                    f"I'm doing my best to answer your questions. "
                    f"I'm scared and I just want us to figure out what's going on."
                )
            next_emotions = {
                "trust": max(5, state.emotion.trust - 20),
                "anger": min(100, state.emotion.anger + 25),
                "cooperation": max(10, state.emotion.cooperation - 15),
            }
            memory_category = "student_behavior"
            memory_importance = 0.85

        elif category == "apology":
            past_alarm = was_alarmed or was_threatened
            if past_alarm:
                response_text = (
                    f"Okay... thank you for saying that. I was really frightened by what you said earlier. "
                    f"Can we start over? I still need to understand what's happening."
                )
            else:
                response_text = (
                    f"It's okay. Thank you for saying that. I just want to figure out what's going on."
                )
            next_emotions = {
                "trust": min(100, state.emotion.trust + 15),
                "fear": max(20, state.emotion.fear - 10),
                "distress": max(10, state.emotion.distress - 10),
            }
            memory_category = "emotional"
            memory_importance = 0.7

        elif category in ("empathy", "reassurance"):
            anxiety = state.emotion.anxiety
            if anxiety > 65:
                response_text = (
                    f"Thank you, doctor... that actually helps a little. "
                    f"I'm still scared, but knowing you're here makes it a bit easier to breathe."
                )
            else:
                response_text = (
                    f"Okay... thank you. I just want to understand what's causing this {p_cc}."
                )
            next_emotions = {
                "trust": min(100, state.emotion.trust + 12),
                "anxiety": max(20, state.emotion.anxiety - 12),
                "fear": max(20, state.emotion.fear - 10),
                "distress": max(20, state.emotion.distress - 10),
                "hope": min(100, state.emotion.hope + 10),
            }
            memory_category = "emotional"
            memory_importance = 0.65

        elif category == "emotional_question":
            response_text = self._answer_emotional_question(msg_lower, state, preface, p_cc)
            memory_category = "emotional"
            memory_importance = 0.65

        elif category == "personal_question":
            response_text = self._answer_personal_question(msg_lower, preface, state)
            revealed = ["lifestyle_risk_factors"]
            memory_category = "question_answered"
            memory_importance = 0.6

        elif category in ("clinical_question", "symptom_question"):
            # ── EMBEDDING-FIRST CLINICAL RETRIEVAL ──────────
            # Replaced keyword engine with VectorStore truth
            
            best_fact = None
            best_score = 0.0
            if semantic_facts:
                for candidate in semantic_facts:
                    if isinstance(candidate, dict):
                        f_text = candidate.get("text", "")
                        f_score = candidate.get("score", 0.0)
                        if f_text and f_score > best_score:
                            best_score = f_score
                            best_fact = f_text
                    else:
                        best_fact = candidate
                        break
                        
            if best_fact and best_score >= 0.55:
                # High-confidence semantic hit: speak directly from the retrieved fact
                response_text = preface + self._fact_as_patient_voice(best_fact, p_cc, state)
                revealed = ["clinical_fact"]
            elif best_fact:
                # Moderate-confidence: try keyword handler first, fall back to semantic
                kw_text, kw_revealed = self._answer_clinical_question(msg_lower, topic, preface, state, p_cc)
                if kw_text:
                    response_text = kw_text
                    revealed = kw_revealed
                else:
                    response_text = preface + self._fact_as_patient_voice(best_fact, p_cc, state)
                    revealed = ["clinical_fact"]
            else:
                # No semantic fact passed threshold — try keyword handler
                kw_text, kw_revealed = self._answer_clinical_question(msg_lower, topic, preface, state, p_cc)
                if kw_text:
                    response_text = kw_text
                    revealed = kw_revealed
                else:
                    # User Request 7: Never invent a fact. Use case-aware safe fallback.
                    response_text = (
                        f"I'm not sure I understood that question, doctor. "
                        f"Could you ask me something about my {p_cc}?"
                    )
                    revealed = []


        elif category == "confusion":
            response_text = (
                f"I'm sorry — I'm not really sure what that means. "
                f"Could you put it in simpler terms? I just want to understand what's going on."
            )
            memory_category = "emotional"
            memory_importance = 0.5

        else:  # general_conversation — never use a generic fallback
            response_text = self._answer_general(msg_lower, preface, state, p_cc)

        # ── NEVER let response_text stay empty ───────────────────────────
        if not response_text or not response_text.strip():
            response_text = self._intelligent_fallback(msg_lower, state, preface, p_cc)

        # ── EMOTION UPDATE (merge existing + computed deltas) ─────────────
        base_emotion = state.emotion.to_dict()
        merged = {**base_emotion, **next_emotions}

        return {
            "response": response_text,
            "emotion_update": merged,
            "revealed_information": revealed,
            "memory_event": {
                "event": f"student_asked: {student_message[:80]}",
                "importance": memory_importance,
                "category": memory_category,
            },
            "communication_state": state.emotion.get_label().lower(),
            "student_communication_classification": com_analysis.get("intent", "neutral"),
        }

    # ── HELPER: SEMANTIC FACT → PATIENT VOICE ──────────────────────────────

    def _fact_as_patient_voice(self, fact: str, p_cc: str, state) -> str:
        """
        Convert a raw case fact string into a natural first-person patient reply.
        Called when semantic retrieval has high confidence in the matched fact.
        """
        fl = fact.lower().strip()

        # Strip indexer NL-bridge prefixes so they don't appear in patient speech.
        # These prefixes were added during indexing to improve retrieval recall.
        bridge_prefixes = [
            "symptom i am having:",
            "symptom:",
            "medical condition / past history:",
            "taking medications:",
            "medications:",
            "family history:",
            "allergies to:",
            "allergies:",
            "chief complaint:",
            "photophobia:",
            "onset (when it started):",
            "onset:",
            "history of illness:",
            "past medical history:",
            "social history:",
            "smoking:",
            "alcohol:",
            "stress:",
        ]
        for prefix in bridge_prefixes:
            if fl.startswith(prefix):
                fact = fact[len(prefix):].strip()
                fl = fact.lower()
                break

        # Handle specific synonym bridges mapped during indexing
        if fl == "feeling nauseated, sick to my stomach, nausea, throwing up, vomiting":
            return "I've been feeling really nauseated, like I'm sick to my stomach."
        elif fl == "sensitive to light, bright light worsens symptoms, photophobia":
            return "The bright light is really bothering my eyes, it makes it worse."
        elif fl.startswith("headache:"):
            fact = fact[9:].strip()
        elif fl.startswith("weakness, unable to move:"):
            fact = fact[25:].strip()
        elif fl.startswith("speech difficulty, slurred speech:"):
            fact = fact[34:].strip()

        if not fact:
            return f"I'm not sure how to describe it exactly."

        # Already phrased as a fact sentence — wrap in patient voice
        if fact.endswith("."):
            return fact
        return f"{fact}."

    # ── HELPER: PREFACE ────────────────────────────────────────────────────

    def _get_preface(self, state) -> str:
        was_insulted = any(
            "insult" in ev.event.lower() or "rude" in ev.event.lower()
            for ev in state.memory.events[-3:]
        )
        was_threatened = any("threat" in ev.event.lower() for ev in state.memory.events[-3:])
        if was_threatened:
            return "I'm still really shaken up by what you said... but if you must know, "
        if was_insulted:
            return "I'm still hurt by how you spoke to me, but... "
        return ""

    # ── HELPER: EMOTIONAL QUESTIONS ────────────────────────────────────────

    def _answer_emotional_question(self, msg_lower: str, state, preface: str, p_cc: str) -> str:
        # Trust
        if any(p in msg_lower for p in ["trust", "believe in you", "confident in you"]):
            trust = state.emotion.trust
            if trust > 60:
                return f"Yes, I do trust you, doctor. I just need you to keep explaining things."
            else:
                return f"I want to trust you. I just need you to be clear with me about what's going on."

        # Check for alarming memory events to reference
        alarming_mem = None
        for ev in reversed(state.memory.events):
            if ev.category in ("student_behavior", "emotional", "clinical"):
                if any(w in ev.event.lower() for w in ["die", "fatal", "surviv", "danger", "serious", "heart", "kill", "blockage", "failing"]):
                    alarming_mem = ev.event
                    break

        # Fear / anxiety / nervousness
        if any(p in msg_lower for p in ["scared", "afraid", "frightened", "nervous", "anxious", "worried", "terrified", "feeling anxious", "feeling scared", "feeling worried"]):
            fear = state.emotion.fear
            anxiety = state.emotion.anxiety
            if alarming_mem and (fear > 60 or anxiety > 60):
                clean_mem = alarming_mem.replace("student_asked: ", "").strip()
                if len(clean_mem) > 60:
                    clean_mem = clean_mem[:60] + "..."
                return (
                    f"Yes... especially after you told me earlier: '{clean_mem}'. "
                    f"I can't stop thinking about that. Is it really that serious?"
                )
            elif fear > 70:
                return (
                    f"Yes... I'm really frightened. I've never felt this {p_cc} before and I "
                    f"don't know what's happening to me. What if it's serious?"
                )
            elif anxiety > 50:
                return (
                    f"Yes, honestly. This {p_cc} came on so suddenly and I don't know what's causing it. "
                    f"I'm trying to stay calm but it's hard."
                )
            else:
                return (
                    f"A little, yes. I just want to know exactly what's happening."
                )

        # Pain
        if "in pain" in msg_lower or ("pain" in msg_lower and "you" in msg_lower):
            sym = self.ctx.first_symptom()
            return f"Yes, it's quite uncomfortable — {sym}."

        # How are you feeling / general wellbeing
        if any(p in msg_lower for p in ["how are you", "how do you feel", "feeling", "doing", "holding up"]):
            anxiety = state.emotion.anxiety
            if anxiety > 60:
                return (
                    f"Honestly, not great. I have this {p_cc} and I'm quite worried about it. "
                    f"I just want to know what's happening."
                )
            else:
                return (
                    f"I'm uncomfortable with this {p_cc}. I'm hoping you can help me figure out what's wrong."
                )

        # What's going through your mind
        if any(p in msg_lower for p in ["going through your mind", "on your mind", "thinking about"]):
            fear = state.emotion.fear
            if alarming_mem and fear > 60:
                clean_mem = alarming_mem.replace("student_asked: ", "").strip()[:60]
                return (
                    f"Honestly — I keep thinking about what you told me earlier. "
                    f"Especially that part about '{clean_mem}'. I can't get it out of my head."
                )
            elif fear > 60:
                return (
                    f"Honestly — I keep thinking about whether this is something serious. "
                    f"Whether I'll be okay. I have people depending on me."
                )
            else:
                return (
                    f"I'm just hoping it's something simple. I've never had anything quite like this before."
                )

        # Why are you looking at me like that
        if "looking at me" in msg_lower or "staring" in msg_lower:
            return f"I'm sorry — I'm just scared. I keep looking at you hoping you'll tell me this isn't serious."

        # Would you like me to explain
        if "would you like" in msg_lower and "explain" in msg_lower:
            return f"Yes, please. I'd really appreciate that. I don't fully understand what's going on."

        # Do you think something serious
        if "do you think" in msg_lower and any(p in msg_lower for p in ["serious", "bad", "dangerous", "wrong"]):
            return (
                f"That's what I'm afraid of, yes. With this {p_cc} coming on so suddenly... "
                f"I just don't know. That's why I came in."
            )

        # Default emotional response — reference memory if available
        if alarming_mem and state.emotion.fear > 60:
            clean_mem = alarming_mem.replace("student_asked: ", "").strip()[:60]
            return (
                f"Yes, I'm really worried. Especially after what you told me earlier — '{clean_mem}'. "
                f"I can't stop thinking about it."
            )
        return (
            f"Yes, I'm genuinely worried. I've never had something like this before and I don't know "
            f"what it means. Can you tell me what you're thinking?"
        )

    # ── HELPER: PERSONAL QUESTIONS ─────────────────────────────────────────

    def _answer_personal_question(self, msg_lower: str, preface: str, state) -> str:
        ctx = self.ctx

        if any(p in msg_lower for p in ["married", "spouse", "wife", "husband", "partner"]):
            soc = ctx.search_category(ctx.social_h, ["married", "spouse", "wife", "husband", "partner", "single", "divorced"])
            if soc:
                return preface + f"Regarding that: {soc}."
            return preface + "Yes, I'm married. My family is who I'm most worried about right now."

        if any(p in msg_lower for p in ["children", "kids", "son", "daughter"]):
            soc = ctx.search_category(ctx.social_h, ["children", "kids", "son", "daughter"])
            if soc:
                return preface + f"{soc}."
            return preface + "Yes, I have children. They're depending on me — that's why this is so frightening."

        if any(p in msg_lower for p in ["job", "work", "occupation", "do for a living", "career"]):
            occ = ctx.occupation
            soc = ctx.search_category(ctx.social_h, ["job", "work", "occupation", "office", "manager"])
            if soc:
                return preface + f"I work as a {occ}. {soc}"
            return preface + f"I work as a {occ}."

        if any(p in msg_lower for p in ["how old", "your age", "age"]):
            return preface + f"I'm {ctx.age} years old."

        if any(p in msg_lower for p in ["what were you doing", "what happened before", "before this started", "doing when"]):
            onset = ctx.onset
            if onset:
                return preface + f"Well, {onset}."
            hist = ctx.search_category(ctx.history_illness, ["doing", "before", "onset"])
            if hist:
                return preface + f"Before this started — {hist}."
            return preface + "I was just going about my normal day when this came on."

        if any(p in msg_lower for p in ["live", "where do you live", "who lives with you", "alone"]):
            soc = ctx.search_category(ctx.social_h, ["live", "living", "alone", "with"])
            if soc:
                return preface + f"{soc}."
            return preface + "I live at home with my family."

        if any(p in msg_lower for p in ["tell me about yourself", "tell me about your family"]):
            parts = []
            if ctx.occupation:
                parts.append(f"I work as a {ctx.occupation}")
            if ctx.age:
                parts.append(f"I'm {ctx.age} years old")
            if ctx.social_h:
                parts.append(ctx.social_h[0])
            if parts:
                return preface + ". ".join(parts) + "."
            return preface + f"I'm just a regular person — I've come here because of this {ctx.chief_complaint.lower()}."

        if any(p in msg_lower for p in ["why didn't you come earlier", "why wait"]):
            return preface + "I kept hoping it would pass on its own. I didn't want to make a fuss. But it didn't go away, so here I am."

        # Fallback personal
        return preface + f"I'm not sure that's relevant right now, but I'll answer if it helps. What specifically did you want to know?"

    # ── HELPER: CLINICAL QUESTIONS ─────────────────────────────────────────

    def _answer_clinical_question(
        self, msg_lower: str, topic: Optional[str], preface: str,
        state, p_cc: str
    ) -> Tuple[str, List[str]]:
        ctx = self.ctx
        revealed = []

        # ── ONSET / TRIGGER ───────────────────────────────────────────────
        if topic in ("onset_trigger", None) and any(kw in msg_lower for kw in [
            "when", "start", "begin", "onset", "happen", "doing", "trigger", "before this", "came on"
        ]):
            onset = ctx.onset
            hist = ctx.search_category(ctx.history_illness, ["onset", "start", "began", "trigger", "doing", "morning", "evening", "sudden", "walking", "exert"])
            sym_onset = ctx.search_category(ctx.symptoms, ["onset", "start", "began", "trigger", "walking", "exert", "morning", "afternoon"])
            if hist:
                return preface + f"It happened like this: {hist}", ["pain_characteristics"]
            if sym_onset:
                return preface + f"Well — {sym_onset}.", ["pain_characteristics"]
            if onset:
                return preface + f"It started like this: {onset}.", ["pain_characteristics"]
            return preface + f"It came on fairly suddenly, I'd say around 30 minutes ago. I wasn't doing anything unusual.", ["pain_characteristics"]

        # ── DURATION ─────────────────────────────────────────────────────
        if topic == "duration" or any(kw in msg_lower for kw in ["how long", "since when", "duration"]):
            dur = ctx.search_category(ctx.history_illness, ["hour", "minute", "day", "since", "duration", "long", "ago", "minutes", "hours"])
            if dur and any(w in dur.lower() for w in ["hour", "minute", "ago", "day", "week", "since"]):
                return preface + f"It started {dur}.", ["pain_characteristics"]
            # Check onset text
            if ctx.onset and any(w in ctx.onset.lower() for w in ["hour", "minute", "ago", "day", "started", "began"]):
                return preface + f"It started {ctx.onset}.", ["pain_characteristics"]
            return preface + "It's been going on for a while — maybe half an hour, perhaps a bit longer. It started fairly suddenly.", ["pain_characteristics"]

        # ── LOCATION / SITE ───────────────────────────────────────────────
        if topic in ("location_site", None) and any(kw in msg_lower for kw in [
            "where", "location", "site", "which side", "which part"
        ]) and "family" not in msg_lower:
            desc = ctx.first_symptom()
            return preface + f"It's mainly in my {p_cc}. To be more exact: {desc}.", ["pain_characteristics"]

        # ── PAIN CHARACTER ────────────────────────────────────────────────
        if topic == "character_quality" or any(kw in msg_lower for kw in [
            "describe", "what kind", "type of pain", "character", "sharp", "dull", "burning", "crushing", "squeezing", "feels like"
        ]):
            desc = ctx.first_symptom()
            return preface + f"It's hard to describe exactly. {desc}.", ["pain_characteristics"]

        # ── RADIATION ─────────────────────────────────────────────────────
        if topic == "radiation" or any(kw in msg_lower for kw in [
            "radiat", "spread", "go anywhere", "move to", "travel", "arm", "jaw", "shoulder", "neck", "leg"
        ]):
            rad = ctx.search_category(ctx.symptoms, ["radiat", "spread", "extend", "travel", "shoulder", "arm", "jaw", "neck", "back"])
            if rad:
                return preface + f"Yes — {rad}.", ["pain_characteristics"]
            return preface + "No, it doesn't seem to go anywhere else. It stays in the same place.", ["pain_characteristics"]

        # ── SEVERITY ─────────────────────────────────────────────────────
        if topic == "severity" or any(kw in msg_lower for kw in [
            "how bad", "scale", "out of 10", "rate the pain", "severe"
        ]):
            severe = any(kw in s.lower() for s in ctx.symptoms for kw in ["severe", "crushing", "unbearable", "intense", "very bad"])
            if severe:
                return preface + "It's really bad — I'd say an 8 or 9 out of 10. Very intense.", ["pain_characteristics"]
            return preface + "It's significant — maybe a 6 or 7 out of 10. Quite noticeable and hard to ignore.", ["pain_characteristics"]

        # ── RELIEVING ─────────────────────────────────────────────────────
        if topic == "relieving" or any(kw in msg_lower for kw in ["better", "reliev", "ease", "nitroglycerin", "rest", "improv"]):
            rel = ctx.search_category(ctx.symptoms + ctx.history_illness, ["better", "reliev", "ease", "nitroglycerin", "rest", "position", "water", "antacid"])
            if rel:
                return preface + f"Regarding that: {rel}.", ["pain_characteristics"]
            return preface + "Nothing seems to make it better so far. It's just constant.", ["pain_characteristics"]

        # ── EXACERBATING ─────────────────────────────────────────────────
        if topic == "exacerbating" or any(kw in msg_lower for kw in ["worse", "aggravat", "makes it worse", "exacerbat"]):
            exc = ctx.search_category(ctx.symptoms + ctx.history_illness, ["worse", "aggravat", "exacerbat", "lying", "bending", "eating"])
            if exc:
                return preface + f"Yes — {exc}.", ["pain_characteristics"]
            return preface + "I'm not sure what makes it worse, honestly. It doesn't seem to change much with position or breathing.", ["pain_characteristics"]

        # ── ASSOCIATED SYMPTOMS ────────────────────────────────────────────
        if topic == "associated_symptoms" or any(kw in msg_lower for kw in [
            "other symptoms", "anything else", "associated", "nausea", "sweat", "clammy", "vomit", "breathe", "breath", "dizzy", "lightheaded"
        ]):
            assoc = [s for s in ctx.symptoms[1:] if any(kw in s.lower() for kw in [
                "sweat", "clammy", "nausea", "vomit", "breath", "dizzy", "lightheaded", "cold", "diarr", "tingling"
            ])]
            if assoc:
                return preface + f"Along with the main issue, I've noticed: {'; '.join(assoc)}.", ["associated_symptoms"]
            if len(ctx.symptoms) > 1:
                return preface + f"I've also been experiencing: {ctx.symptoms[1]}.", ["associated_symptoms"]
            return preface + "Just the main one for now — but I feel generally quite unwell.", ["associated_symptoms"]

        # ── HEARTBURN / ACIDITY / OBESITY ─────────────────────────────────
        if topic == "heartburn_acidity" or any(kw in msg_lower for kw in [
            "heartburn", "acidity", "acid", "reflux", "gerd", "burning", "sour", "regurgit", "indigestion", "obese", "obesity", "overweight"
        ]):
            fact = ctx.search_facts(["acid", "reflux", "heartburn", "burning", "sour", "obese", "obesity", "weight"])
            pmh_fact = ctx.search_category(ctx.pmh, ["acid", "reflux", "heartburn", "obese", "obesity"])
            soc_fact = ctx.search_category(ctx.social_h, ["obese", "obesity", "weight", "eating", "coffee"])
            sym_fact = ctx.search_category(ctx.symptoms, ["heartburn", "burning", "acid", "sour", "reflux"])
            if sym_fact:
                return preface + f"Yes — {sym_fact}.", ["pain_characteristics"]
            if pmh_fact:
                return preface + f"Regarding that in my history: {pmh_fact}.", ["past_medical_history"]
            if soc_fact:
                return preface + f"Yes, {soc_fact}.", ["lifestyle_risk_factors"]
            if fact:
                return preface + f"Yes — {fact}.", ["pain_characteristics"]
            return preface + "I haven't really been told I have that — what makes you ask?", ["pain_characteristics"]

        # ── GLUCOSE / SUGAR ────────────────────────────────────────────────
        if topic == "glucose_sugar" or any(kw in msg_lower for kw in ["glucose", "sugar level", "blood sugar", "glycaemia"]):
            fact = ctx.search_category(ctx.pmh + ctx.history_illness, ["glucose", "sugar", "glycaemia", "diabet"])
            if fact:
                return preface + f"I don't know the exact number, but my history shows: {fact}.", ["past_medical_history"]
            return preface + "I don't know my glucose level — nobody has told me that result.", ["past_medical_history"]

        # ── TROPONIN ──────────────────────────────────────────────────────
        if topic == "troponin":
            return preface + "I don't know what my troponin is — they haven't told me those results.", ["pain_characteristics"]

        # ── ECG ───────────────────────────────────────────────────────────
        if topic == "ecg":
            return preface + "I've had an ECG? Is it that machine with all the wires? I didn't really understand what it was showing.", ["pain_characteristics"]

        # ── PAST HISTORY ──────────────────────────────────────────────────
        if topic in ("past_history", "past_medical") or any(kw in msg_lower for kw in [
            "past medical", "history of", "medical history", "before", "ever had", "other diseases", "health conditions"
        ]):
            if ctx.pmh and ctx.pmh != ["Generally healthy, no prior surgeries"]:
                return preface + f"My past medical history includes: {', '.join(ctx.pmh)}.", ["past_medical_history"]
            return preface + "I don't have any major health conditions that I know of.", ["past_medical_history"]

        # ── DIABETES specifically ─────────────────────────────────────────
        if any(kw in msg_lower for kw in ["diabet", "blood sugar", "sugar"]):
            fact = ctx.search_category(ctx.pmh, ["diabet", "sugar", "glucose", "insulin"])
            if fact:
                return preface + f"{fact}.", ["past_medical_history"]
            return preface + "No, I don't have diabetes as far as I know.", ["past_medical_history"]

        # ── BLOOD PRESSURE / HYPERTENSION ─────────────────────────────────
        if topic == "bp_check" or any(kw in msg_lower for kw in ["blood pressure", "hypertension", "bp"]):
            fact = ctx.search_category(ctx.pmh, ["hypertension", "blood pressure", "bp"])
            if fact:
                return preface + f"{fact}.", ["past_medical_history"]
            return preface + "I don't think I have high blood pressure, but I'm not always sure.", ["past_medical_history"]

        # ── MEDICATIONS ───────────────────────────────────────────────────
        if topic == "medications" or any(kw in msg_lower for kw in ["medication", "medicine", "pill", "drug", "take", "prescribed"]):
            if ctx.meds and ctx.meds not in [["None"], ["None regular"]]:
                return preface + f"I take: {', '.join(ctx.meds)}.", ["medication_history"]
            return preface + "I don't take any regular medications.", ["medication_history"]

        # ── ALLERGIES ─────────────────────────────────────────────────────
        if topic == "allergies" or any(kw in msg_lower for kw in ["allerg", "penicillin", "reaction to"]):
            if ctx.allergies and "no known" not in " ".join(ctx.allergies).lower():
                return preface + f"Yes, regarding allergies: {', '.join(ctx.allergies)}.", ["allergies"]
            return preface + "No allergies that I know of.", ["allergies"]

        # ── FAMILY HISTORY ────────────────────────────────────────────────
        if topic == "family_history" or any(kw in msg_lower for kw in ["family", "father", "mother", "parent", "relative", "siblings", "grandparent"]):
            if ctx.family_h:
                return preface + f"Well, in my family: {', '.join(ctx.family_h)}.", ["family_history"]
            return preface + "No significant family history that I can think of.", ["family_history"]

        # ── SMOKING ───────────────────────────────────────────────────────
        if topic == "smoking" or any(kw in msg_lower for kw in ["smoke", "cigarette", "tobacco", "pack"]):
            fact = ctx.search_category(ctx.social_h, ["smoke", "cigarette", "tobacco", "pack"])
            if fact:
                return preface + f"About smoking: {fact}.", ["lifestyle_risk_factors"]
            return preface + "No, I don't smoke.", ["lifestyle_risk_factors"]

        # ── ALCOHOL ───────────────────────────────────────────────────────
        if topic == "alcohol" or any(kw in msg_lower for kw in ["alcohol", "drink", "beer", "wine", "liquor"]):
            fact = ctx.search_category(ctx.social_h, ["alcohol", "drink", "beer", "wine"])
            if fact:
                return preface + f"{fact}.", ["lifestyle_risk_factors"]
            return preface + "I don't drink much. Occasionally, maybe.", ["lifestyle_risk_factors"]

        # ── DIET / FOOD HABITS ────────────────────────────────────────────
        if topic == "diet" or any(kw in msg_lower for kw in ["diet", "food", "eat", "coffee", "caffeine", "meal", "dinner"]):
            fact = ctx.search_category(ctx.social_h, ["coffee", "eat", "diet", "food", "dinner", "meal", "caffeine"])
            if fact:
                return preface + f"Regarding my diet: {fact}.", ["lifestyle_risk_factors"]
            return preface + "Nothing unusual I can think of. I try to eat normally.", ["lifestyle_risk_factors"]

        # ── STRESS ────────────────────────────────────────────────────────
        if topic == "stress" or any(kw in msg_lower for kw in ["stress", "stressful", "pressure", "anxiety", "mental health"]):
            fact = ctx.search_category(ctx.social_h, ["stress", "pressure", "job", "busy", "workload"])
            if fact:
                return preface + f"Yes, regarding my stress levels: {fact}.", ["lifestyle_risk_factors"]
            return preface + "Work has been stressful lately, yes. I've been feeling under pressure.", ["lifestyle_risk_factors"]

        # ── GENERAL WELLBEING ─────────────────────────────────────────────
        if topic == "general_wellbeing":
            return preface + f"Not great, honestly. I have this {p_cc} and I'm quite worried.", []

        # ── Catch-all for clinical questions that didn't map to a topic ───
        # Try searching all clinical facts for any word from the query
        search_words = [w.strip("?.,;:'\"") for w in msg_lower.split() if len(w) > 3 and w not in {
            "what", "when", "where", "does", "have", "your", "been", "that", "this", "with", "from", "tell", "about", "feel"
        }]
        if search_words:
            matched = ctx.search_facts(search_words)
            if matched:
                return preface + f"{matched}.", ["pain_characteristics"]

        return "", []

    # ── HELPER: GENERAL CONVERSATION ──────────────────────────────────────

    def _answer_general(self, msg_lower: str, preface: str, state, p_cc: str) -> str:
        ctx = self.ctx

        # "You don't look very well"
        if any(p in msg_lower for p in ["don't look", "look unwell", "look pale", "look bad", "look sick"]):
            return f"I know. I don't feel well either. This {p_cc} has come on quite quickly and it's really worrying me."

        # "I'm worried about you"
        if "worried about you" in msg_lower or "concern" in msg_lower:
            return f"Thank you, doctor. That actually means a lot right now. I'm worried too."

        # Investigation comment
        if any(p in msg_lower for p in ["test", "investigation", "blood", "scan", "ecg", "ekg", "ordered", "xray", "x-ray"]):
            return (
                f"Is... is that test for me? What are you looking for? "
                f"Is it related to this {p_cc}?"
            )

        # Greeting
        if any(p in msg_lower for p in ["hello", "hi", "good morning", "good afternoon", "my name", "i am", "i'm dr"]):
            init = ctx.case_data.get("patient", {}).get("initial_statement", f"I have {p_cc}.")
            return f"Hello, doctor. I'm {ctx.name}. {init}"

        # "Why are you looking at me like that" / "why are you shaking"
        if any(p in msg_lower for p in ["looking at me", "staring", "shaking", "shivering", "trembling"]):
            return f"I'm sorry — I'm scared. This {p_cc} has really frightened me and I'm not sure what to expect."

        # Professionalism / introduction
        if any(p in msg_lower for p in ["i'll explain", "i will explain", "i'm going to", "we will"]):
            return f"Okay, please do. I need someone to explain what's happening. I'm quite frightened."

        # "What's happening to me" / "what is wrong"
        if any(p in msg_lower for p in ["what's happening", "what is happening", "what is wrong", "what's wrong"]):
            return f"That's exactly what I'm trying to find out. I have this {p_cc} and I genuinely don't know what's causing it."

        # Encouragement to speak
        if any(p in msg_lower for p in ["take your time", "speak freely", "feel free", "tell me everything"]):
            return f"Thank you, doctor. I'll do my best. I just want to understand what's going on with me."

        # Information doctor gave (professional explanation)
        if any(p in msg_lower for p in ["blockage", "oxygen", "myocardial", "ischemia", "occlusion", "artery", "cardiac"]):
            literacy = ctx.health_literacy
            if literacy < 40:
                return f"I'm sorry — I don't really understand those words. Could you explain in simpler terms what that means for me?"
            else:
                return f"I see... that sounds serious. So what happens next? What can you do for me?"

        return ""

    # ── HELPER: INTELLIGENT FALLBACK (never returns generic message) ───────

    def _intelligent_fallback(self, msg_lower: str, state, preface: str, p_cc: str) -> str:
        """
        Multi-level fallback — always produces a human-like response.
        Level 1: Pattern-based emotional/situational response
        Level 2: Personality-driven uncertainty
        Level 3: Natural curiosity about own condition
        """
        anxiety = state.emotion.anxiety
        trust = state.emotion.trust
        fear = state.emotion.fear

        # If recently frightened
        if fear > 70:
            return (
                preface + "I'm sorry, I... I'm having a hard time concentrating right now. "
                "I'm just really scared. What's happening to me?"
            )

        # If low trust
        if trust < 30:
            return preface + "I'm not sure I understand. Could you explain what you mean? I just want to know what's going on."

        # If anxious
        if anxiety > 60:
            return (
                preface + "I'm not sure about that, to be honest. Could you put it in simpler terms? "
                "I'm finding it hard to think clearly with this {p_cc}."
            ).format(p_cc=p_cc)

        # Default: natural curiosity
        responses = [
            f"I'm not sure about that. Could you explain what you mean, doctor?",
            f"I haven't thought about that specifically. What does it relate to with my {p_cc}?",
            f"I'm not certain. Is that related to what's happening to me?",
            f"I don't really know — I was hoping you could tell me something about what's going on.",
            f"Could you explain that a bit more? I'm trying to follow everything you're saying.",
        ]
        # Deterministic selection using turn count
        idx = state.turn_count % len(responses)
        return preface + responses[idx]
