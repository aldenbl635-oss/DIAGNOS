"""
Student communication classifier and LLM output parser.
Classifies how the student communicates and parses structured agent output.
"""
import json
import re
from typing import Dict, Any, Tuple, List

# Communication style keywords for classification
COMMUNICATION_PATTERNS = {
    "alarmist": [
        "you're going to die", "you will die", "you are going to die", "you are dying",
        "you're dying", "very serious", "critical", "emergency",
        "heart attack", "you might die", "fatal", "dangerous", "life-threatening",
        "don't wait", "immediately", "urgent", "alarming", "concerning result",
        "not good", "bad news", "very bad", "serious condition", "grave",
        "you won't survive", "it doesn't look good", "we may not be able to save",
    ],
    "dismissive": [
        "stop wasting", "just answer", "hurry up", "quickly", "don't worry about that",
        "irrelevant", "doesn't matter", "forget it", "next question", "moving on",
        "not important", "shut up", "stop talking", "be quiet", "don't care", "irrelevant"
    ],
    "empathetic": [
        "i understand", "i know this is", "i can see", "that must be", "i'm sorry",
        "it's okay", "you're doing great", "i appreciate", "thank you for telling",
        "i hear you", "don't worry", "we'll take care", "i'll explain", "let me explain",
        "understandably", "of course", "feel for you", "tough", "difficult", "painful",
        "how are you feeling", "sorry to hear"
    ],
    "reassuring": [
        "you're safe", "we're going to help", "you'll be okay", "we're here",
        "good care", "in good hands", "we'll take care of", "the team is",
        "everything we can", "appropriate steps", "best care", "everything will be fine",
        "everything will be okay", "fine", "reassure"
    ],
    "respectful": [
        "please", "thank you", "could you", "would you mind", "i appreciate",
        "if you're comfortable", "when you're ready", "take your time",
    ],
    "confusing": [
        "st elevation", "stemi", "troponin elevation", "myocardial", "ischemia",
        "angiography", "percutaneous", "catheterization", "hemodynamic",
        "reperfusion", "thrombolysis",
    ],
    "rushed": [
        "quickly", "fast", "hurry", "rapid", "asap", "right now", "immediately tell me",
        "no time", "we need to know now", "hurry up", "we don't have all day"
    ],
    "neutral": [],  # Default fallback
}

# Phrases that constitute a direct existential threat to the patient
EXISTENTIAL_THREAT_PHRASES = [
    "you're going to die", "you are going to die", "you will die", "you are dying",
    "you're dying", "you won't survive", "it's fatal", "you may not make it",
    "we may not be able to save you", "you don't have long", "you could die",
    "you might not survive", "gonna die", "going to die", "gonna pass away",
    "think you are gonna die", "think you're gonna die", "think you are going to die",
    "think you're going to die", "you'll die", "you're dead", "you are dead",
    "might die", "may die", "will pass away", "going to pass away"
]


def map_revealed_fact_to_category(fact: str) -> str:
    """Map any loose revealed fact to one of the 7 scoring history categories."""
    fact_lower = fact.lower()
    if any(x in fact_lower for x in ["pain", "radiat", "onset", "exert", "duration", "location", "character"]):
        return "pain_characteristics"
    if any(x in fact_lower for x in ["smoke", "tobacco", "lifestyle", "habit", "stress", "alcohol", "exercise", "occupation"]):
        return "lifestyle_risk_factors"
    if any(x in fact_lower for x in ["diabet", "sugar", "hypertension", "cholesterol", "pressure", "cardiac history", "past_medical", "lisinopril", "metformin"]):
        return "past_medical_history"
    if any(x in fact_lower for x in ["sweat", "diaphoresis", "nausea", "vomit", "breath", "dyspnea", "associated"]):
        return "associated_symptoms"
    if any(x in fact_lower for x in ["father", "family", "mother", "paternal", "relative"]):
        return "family_history"
    if any(x in fact_lower for x in ["medication", "lisinopril", "metformin", "atorvastatin", "drug", "pill", "prescrib"]):
        return "medication_history"
    if any(x in fact_lower for x in ["allerg", "nkda"]):
        return "allergies"
    return "other"


def analyze_student_communication_rule_based(message: str) -> Dict[str, Any]:
    """
    Categorizes the student's message into emotional, social, and semantic properties.
    Returns:
        {
            "intent": str,
            "tone": str,
            "severity": int (0-100),
            "contains_insult": bool,
            "contains_threat": bool,
            "empathetic": bool,
            "reassuring": bool,
            "patient_relevant": bool
        }
    """
    msg_lower = message.lower()
    
    intent = "neutral"
    tone = "calm"
    severity = 10
    contains_insult = False
    contains_threat = False
    empathetic = False
    reassuring = False
    patient_relevant = False

    # 1. Threatening (critical check)
    threat_patterns = [
        "hurt you", "hit you", "kill you", "beat you", "slap you", "punch you",
        "sue you", "report you", "sued", "regret this", "threatening", "kick you",
        "lock you", "jail", "arrest"
    ]
    
    # 2. Frightening / Alarmist
    frightening_patterns = [
        "going to die", "will die", "are dying", "dying", "won't survive",
        "cannot save you", "deadly", "fatal", "you're dead", "you'll die",
        "emergency", "critical", "grave danger", "very serious", "might die",
        "may die", "you might die"
    ]
    
    # 3. Insulting (Swearing/Swearwords)
    insult_patterns = [
        "stfu", "idiot", "stupid", "moron", "fool", "dumb", "bitch", "asshole",
        "morons", "pathetic", "shut up", "shutup", "fucking", "bastard"
    ]

    # 4. Rude
    rude_patterns = [
        "annoying", "whatever", "get lost", "talk to the hand", "waste of time",
        "wasting my time", "useless", "incompetent", "losers", "shame on you"
    ]

    # 5. Dismissive
    dismissive_patterns = [
        "stop wasting", "just answer", "don't worry about that", "irrelevant",
        "doesn't matter", "forget it", "next question", "moving on", "not important",
        "be quiet", "don't care", "shut up"
    ]

    # 6. Impatient / Rushed
    rushed_patterns = [
        "hurry", "quickly", "fast", "asap", "rapid", "right now", "immediately tell me",
        "no time", "we need to know now", "we don't have all day", "be quick"
    ]

    # 7. Confusing (medical jargon)
    confusing_patterns = [
        "myocardial", "stemi", "ischemia", "catheterization", "reperfusion",
        "hemodynamic", "troponin elevation", "st elevation", "thrombolysis"
    ]

    # 8. Reassuring
    reassuring_patterns = [
        "you're safe", "you'll be okay", "we're here", "good care", "in good hands",
        "take care of you", "everything will be fine", "everything will be okay",
        "fine", "appropriate steps", "reassure"
    ]

    # 9. Empathetic
    empathetic_patterns = [
        "i understand", "i know this is", "i can see", "that must be", "i'm sorry",
        "sorry to hear", "feel for you", "it's okay", "take your time", "appreciate",
        "i hear you", "understandably", "of course"
    ]

    # 10. Respectful
    respectful_patterns = [
        "please", "thank you", "would you mind", "could you", "if you're comfortable",
        "when you're ready"
    ]

    # Priority-based matching chain
    if any(k in msg_lower for k in threat_patterns):
        contains_threat = True
        intent = "threatening"
        tone = "hostile"
        severity = 95
    elif any(k in msg_lower for k in frightening_patterns) or detect_existential_threat(message):
        intent = "frightening"
        tone = "alarmist"
        severity = 90
    elif any(k in msg_lower for k in insult_patterns):
        contains_insult = True
        intent = "insulting"
        tone = "hostile"
        severity = 85
    elif any(k in msg_lower for k in rude_patterns):
        intent = "rude"
        tone = "frustrated"
        severity = 70
    elif any(k in msg_lower for k in dismissive_patterns):
        intent = "dismissive"
        tone = "dismissive"
        severity = 60
    elif any(k in msg_lower for k in rushed_patterns):
        intent = "rushed"
        tone = "impatient"
        severity = 50
    elif any(k in msg_lower for k in confusing_patterns):
        intent = "confusing"
        tone = "technical"
        severity = 40
    elif any(k in msg_lower for k in reassuring_patterns):
        intent = "reassuring"
        tone = "supportive"
        reassuring = True
        severity = 25
    elif any(k in msg_lower for k in empathetic_patterns):
        intent = "empathetic"
        tone = "empathetic"
        empathetic = True
        severity = 20
    elif any(k in msg_lower for k in respectful_patterns):
        intent = "respectful"
        tone = "polite"
        severity = 15

    # Check relevance to patient symptoms/questions
    relevance_patterns = [
        "chest", "pain", "pressure", "heart", "arm", "breathe", "sweat", "nausea",
        "onset", "die", "family", "history", "diabetes", "smoke", "allergies",
        "medication", "lisinopril", "metformin", "atorvastatin"
    ]
    if any(k in msg_lower for k in relevance_patterns):
        patient_relevant = True

    return {
        "intent": intent,
        "tone": tone,
        "severity": severity,
        "contains_insult": contains_insult,
        "contains_threat": contains_threat,
        "empathetic": empathetic,
        "reassuring": reassuring,
        "patient_relevant": patient_relevant
    }


def classify_student_communication(message: str) -> str:
    """
    Classify the student's communication style based on message content.
    Returns one of: empathetic, reassuring, respectful, neutral, confusing,
    rushed, dismissive, alarmist, rude, insulting, threatening, frightening
    """
    analysis = analyze_student_communication_rule_based(message)
    return analysis["intent"]


def detect_existential_threat(message: str) -> bool:
    """Return True if the message contains a direct existential threat to the patient's life."""
    msg_lower = message.lower()
    return any(phrase in msg_lower for phrase in EXISTENTIAL_THREAT_PHRASES)


def parse_agent_response(raw_output: str, fallback_text: str = "") -> Dict[str, Any]:
    """
    Parse structured JSON from LLM agent output.
    Returns a dict with guaranteed fields.
    """
    default = {
        "response": fallback_text or "I'm not sure how to respond to that.",
        "emotion_update": {},
        "revealed_information": [],
        "memory_event": None,
        "communication_state": "neutral",
        "student_communication_classification": "neutral",
        "belief_update": None,
    }

    if not raw_output:
        return default

    # Try to extract JSON block
    try:
        # Direct parse
        parsed = json.loads(raw_output.strip())
        return {**default, **parsed}
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in output
    json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            return {**default, **parsed}
        except json.JSONDecodeError:
            pass

    # Extract just the response text if JSON fails
    response_match = re.search(r'"response"\s*:\s*"([^"]*)"', raw_output)
    if response_match:
        default["response"] = response_match.group(1)

    # If we have at least a response, return it
    if default["response"] != fallback_text:
        return default

    # Last resort: treat whole output as response text (strip JSON-like chars)
    clean = re.sub(r'[{}"\\]', '', raw_output).strip()
    if clean:
        default["response"] = clean[:500]  # Truncate if very long

    return default


def compute_emotion_delta_from_style(style: str, personality_sensitivity: int = 50) -> Dict[str, int]:
    """
    Compute a deterministic emotion delta based on student communication style.
    Used in DEMO_MODE and as a fallback when LLM doesn't provide emotion_update.
    """
    # Sensitivity multiplier (0.5x to 1.5x based on personality)
    sensitivity = max(0.5, min(1.5, personality_sensitivity / 50.0))

    base_deltas = {
        "threatening": {"fear": 35, "anxiety": 20, "trust": -25, "distress": 30, "anger": 15, "shock": 40, "sadness": 10},
        "insulting":   {"trust": -25, "anger": 30, "distress": 25, "anxiety": 15, "confusion": 10},
        "rude":        {"trust": -15, "anger": 20, "distress": 10, "anxiety": 10},
        "dismissive":  {"trust": -15, "anger": 15, "distress": 10},
        "rushed":      {"anxiety": 15, "trust": -5, "distress": 5},
        "impatient":   {"anxiety": 10, "trust": -10, "anger": 10},
        "alarmist":    {"fear": 25, "anxiety": 20, "trust": -15, "confusion": 10, "distress": 15, "hope": -10, "shock": 20, "sadness": 10},
        "frightening": {"fear": 35, "anxiety": 25, "trust": -20, "distress": 25, "hope": -20, "shock": 40, "sadness": 15},
        "empathetic":  {"trust": 15, "anxiety": -12, "hope": 8, "distress": -8, "shock": -10, "fear": -10, "anger": -15},
        "reassuring":  {"trust": 12, "anxiety": -15, "hope": 15, "fear": -12, "shock": -15, "anger": -12},
        "respectful":  {"trust": 5, "anxiety": -5},
        "confusing":   {"confusion": 20, "anxiety": 5},
        "neutral":     {"trust": 2},
    }

    raw = base_deltas.get(style, {"trust": 1})
    return {k: int(v * sensitivity) for k, v in raw.items()}


def compute_existential_threat_emotion_spike(fear_of_death: int = 60, emotional_sensitivity: int = 50) -> Dict[str, int]:
    """
    Compute the emotion spike when a patient hears a direct existential threat.
    Modulated by personality (fear_of_death, emotional_sensitivity).
    """
    intensity = max(0.7, min(1.4, (fear_of_death / 60.0 + emotional_sensitivity / 50.0) / 2.0))
    return {
        "shock":   int(min(100, 90 * intensity)),
        "fear":    int(min(100, 85 * intensity)),
        "distress": int(min(100, 75 * intensity)),
        "anxiety": int(min(100, 70 * intensity)),
        "sadness": int(min(100, 60 * intensity)),
        "hope":    max(0, int(15 - (fear_of_death // 10))),  # hope crumbles
        "trust":   -25,  # alarmist statements erode trust
    }

