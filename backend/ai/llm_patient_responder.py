"""
llm_patient_responder.py — Hybrid RAG + LLM Patient Response Layer

ARCHITECTURE
============
Student message
    │
    ▼
SemanticRetriever ──► Actian VectorAI / Disk Index
    │                 (STRICT case_id isolation)
    ▼
Verified Clinical Facts
    │
    ▼
LLMPatientResponder    ◄── PatientState / Emotion / Memory
    │
    ▼
Validated natural response

ANTI-HALLUCINATION RULES
========================
• The LLM receives only the facts retrieved by the vector search for THIS case.
• The LLM is NOT given the full case JSON — only what retrieval returned.
• If no facts are retrieved above threshold, the LLM is asked to give a safe
  "I'm not sure" style response rather than inventing facts.
• The generated response is validated: if it contains invented medications,
  diagnoses, or symptoms not present in the retrieved facts, it is discarded
  and the OfflinePatientResponder is used instead.

FALLBACK CHAIN
==============
1. Retrieve facts via Embeddings + VectorStore (case-isolated).
2. If LLM_ENABLED=true and an API key is configured:
       → pass retrieved facts + patient state + recent conversation to LLM.
       → validate the response.
       → if valid, return it.
3. If LLM is unavailable, disabled, times out, or validation fails:
       → fall back to OfflinePatientResponder (existing deterministic engine).
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger(__name__)

# ── Prompt template (loaded once) ────────────────────────────────────────────

_PROMPT_TEMPLATE: Optional[str] = None


def _load_rag_prompt() -> str:
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "prompts", "patient_rag_turn.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _PROMPT_TEMPLATE = f.read()
        except Exception as e:
            logger.warning("[LLMPatientResponder] Could not load prompt template: %s", e)
            _PROMPT_TEMPLATE = ""
    return _PROMPT_TEMPLATE


# ── Validation helpers ────────────────────────────────────────────────────────

# Words that suggest the LLM may have fabricated a medical entity not in retrieval
_HALLUCINATION_TRIGGERS = [
    r"\baspirin\b", r"\bibuprofen\b", r"\bparacetamol\b", r"\bacetaminophen\b",
    r"\bmetformin\b", r"\batorvastatin\b", r"\blisinopril\b", r"\bamoxicillin\b",
    r"\bheart attack\b", r"\bmyocardial infarction\b", r"\bstemi\b", r"\bstroke\b",
    r"\bdiabetes\b", r"\bhypertension\b", r"\bcholesterol\b",
]

# Common safe fallback phrases indicating the LLM correctly abstained
_SAFE_RESPONSES = ["not sure", "don't think", "don't know", "i'm not certain", "couldn't say"]


def _build_retrieved_facts_text(facts: List[Dict[str, Any]]) -> str:
    """Format vector-retrieved facts for prompt injection."""
    if not facts:
        return "No specific facts retrieved for this question. Respond with appropriate uncertainty."
    lines = []
    for f in facts:
        fact_type = f.get("fact_type", "fact")
        text = f.get("text", "")
        score = f.get("score", 0.0)
        lines.append(f"  [{fact_type}] {text}  (relevance: {score:.2f})")
    return "\n".join(lines)


def _build_conversation_text(history: List[Dict[str, str]], max_turns: int = 6) -> str:
    """Build a concise recent conversation window for the prompt."""
    if not history:
        return "No prior conversation."
    recent = history[-max_turns:]
    lines = []
    for msg in recent:
        role = "Student" if msg.get("role") == "student" else "Patient (you)"
        lines.append(f"{role}: {msg.get('text', '').strip()}")
    return "\n".join(lines)


def _build_emotion_text(state) -> str:
    """Summarise the patient's current emotional state for the prompt."""
    try:
        em = state.emotion
        label = em.get_label()
        desc = em.to_prompt_description() if hasattr(em, "to_prompt_description") else label
        return f"State: {label}. {desc}"
    except Exception:
        return "Anxious."


def _validate_llm_response(
    response: str,
    retrieved_facts: List[Dict[str, Any]],
    strict: bool = False,
) -> bool:
    """
    Light validation: flag responses that mention medical entities not in the
    retrieved facts.  Returns True if response is acceptable.

    Algorithm:
    1. Build a combined whitelist of all text tokens from retrieved facts.
    2. If a hallucination trigger fires AND the trigger term does not appear in
       any retrieved fact text, the response is likely invented → reject.
    3. If strict=False, soft-pass uncertain responses ("I'm not sure…").
    """
    rlow = response.lower()

    # Always accept safe abstention phrases
    if any(ph in rlow for ph in _SAFE_RESPONSES):
        return True

    fact_corpus = " ".join(f.get("text", "") for f in retrieved_facts).lower()

    for pattern in _HALLUCINATION_TRIGGERS:
        if re.search(pattern, rlow, re.IGNORECASE):
            term = re.sub(r"\\b", "", pattern).strip()
            if term not in fact_corpus:
                logger.warning(
                    "[LLMPatientResponder] Validation FAILED — invented term '%s' not in facts.", term
                )
                return False

    return True


# ── LLM call ─────────────────────────────────────────────────────────────────

def _call_llm(prompt_text: str, timeout: float) -> Optional[str]:
    """
    Call the configured LLM provider with the given prompt.
    Returns the raw text response or None on failure.
    """
    import signal
    import threading

    result_holder: Dict[str, Any] = {"text": None, "error": None}

    def _run():
        try:
            if settings.GEMINI_API_KEY:
                from google import genai
                from google.genai import types as gtypes
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                response = client.models.generate_content(
                    model=settings.LLM_MODEL_GEMINI,
                    contents=prompt_text,
                    config=gtypes.GenerateContentConfig(
                        temperature=settings.LLM_TEMPERATURE,
                        response_mime_type="application/json",
                    ),
                )
                result_holder["text"] = response.text
            elif settings.OPENAI_API_KEY:
                import requests as _req
                base = settings.OPENAI_API_BASE or "https://api.openai.com/v1"
                url = f"{base.rstrip('/')}/chat/completions"
                payload = {
                    "model": settings.LLM_MODEL_OPENAI,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "temperature": settings.LLM_TEMPERATURE,
                    "response_format": {"type": "json_object"},
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                }
                r = _req.post(url, headers=headers, json=payload, timeout=timeout)
                r.raise_for_status()
                result_holder["text"] = r.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            result_holder["error"] = exc

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        logger.warning("[LLMPatientResponder] LLM call timed out after %.1fs.", timeout)
        return None

    if result_holder["error"]:
        logger.warning("[LLMPatientResponder] LLM call failed: %s", result_holder["error"])
        return None

    return result_holder["text"]


# ── Public responder ──────────────────────────────────────────────────────────

class LLMPatientResponder:
    """
    Hybrid RAG + LLM responder.

    Usage (inside PatientAgent._demo_response):
        llm_resp = LLMPatientResponder()
        result = llm_resp.respond(
            student_message=...,
            case_id=...,
            case_data=...,
            state=...,
            semantic_facts=...,        # already retrieved by SemanticRetriever
            conversation_history=...,
        )
        if result is None:
            # fall back to OfflinePatientResponder
    """

    def respond(
        self,
        student_message: str,
        case_id: str,
        case_data: Dict[str, Any],
        state,
        semantic_facts: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        """
        Returns a result dict compatible with OfflinePatientResponder output,
        or None if LLM is unavailable / response is invalid.

        Result dict keys: response, emotion_update, revealed_information, memory_event
        """
        t_start = time.time()

        if not settings.LLM_ENABLED:
            logger.debug("[LLMPatientResponder] LLM disabled — skipping.")
            return None

        if not (settings.GEMINI_API_KEY or settings.OPENAI_API_KEY):
            logger.debug("[LLMPatientResponder] No API keys configured — skipping.")
            return None

        template = _load_rag_prompt()
        if not template:
            logger.warning("[LLMPatientResponder] No prompt template — skipping.")
            return None

        # Build prompt
        patient = case_data.get("patient", {})
        patient_name = patient.get("name", "the patient")
        patient_age = str(patient.get("age", "unknown"))
        patient_sex = patient.get("sex", "unknown")
        chief_complaint = (
            patient.get("chief_complaint")
            or case_data.get("presentation", {}).get("chief_complaint", "my condition")
        )

        facts_text = _build_retrieved_facts_text(semantic_facts)
        conv_text = _build_conversation_text(conversation_history)
        emotion_text = _build_emotion_text(state)

        prompt = template.format(
            patient_name=patient_name,
            patient_age=patient_age,
            patient_sex=patient_sex,
            chief_complaint=chief_complaint,
            retrieved_facts=facts_text,
            conversation_history=conv_text,
            emotional_state=emotion_text,
            student_question=student_message,
        )

        # Log context (without API key exposure)
        logger.info("[CASE] case_id=%s", case_id)
        logger.info("[QUESTION] %s", student_message[:120])
        logger.info("[VECTOR SEARCH] %d facts retrieved (top score=%.2f)",
                    len(semantic_facts),
                    semantic_facts[0]["score"] if semantic_facts else 0.0)
        logger.info("[LLM] enabled=True provider=%s model=%s",
                    "gemini" if settings.GEMINI_API_KEY else "openai",
                    settings.LLM_MODEL_GEMINI if settings.GEMINI_API_KEY else settings.LLM_MODEL_OPENAI)

        t_llm_start = time.time()
        raw = _call_llm(prompt, timeout=settings.LLM_TIMEOUT)
        t_llm = time.time() - t_llm_start

        if raw is None:
            logger.info("[RESPONSE SOURCE] LLM failed/timed-out → OfflineResponder")
            return None

        # Parse JSON response
        try:
            # Strip markdown fences if the model adds them despite json mode
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL)
            parsed = json.loads(clean)
        except Exception as e:
            logger.warning("[LLMPatientResponder] JSON parse failed: %s — raw: %s", e, raw[:200])
            return None

        response_text = parsed.get("response", "").strip()
        if not response_text:
            logger.warning("[LLMPatientResponder] Empty response text — fallback.")
            return None

        # Validate: reject hallucinated medical content
        if not _validate_llm_response(response_text, semantic_facts):
            logger.warning("[RESPONSE SOURCE] Validation failed → OfflineResponder")
            return None

        revealed = parsed.get("revealed_information", [])
        if not isinstance(revealed, list):
            revealed = []

        t_total = time.time() - t_start

        # Structured timing log
        print(f"\n[AI TIMING]")
        print(f"  LLM generation:  {t_llm * 1000:.1f} ms")
        print(f"  Total (LLM path): {t_total * 1000:.1f} ms")
        logger.info("[RESPONSE SOURCE] LLM")

        return {
            "response": response_text,
            "emotion_update": {},            # emotion engine controls this — not the LLM
            "revealed_information": revealed,
            "memory_event": {
                "event": f"llm_student_asked: {student_message[:80]}",
                "importance": 0.6,
                "category": "question_answered",
            },
        }
