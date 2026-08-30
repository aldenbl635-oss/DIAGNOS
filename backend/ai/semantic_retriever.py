"""
SemanticRetriever — bridge between student messages and VectorStore.

Converts a student's question into an embedding, searches the case-isolated
vector index, and returns the most relevant patient facts.

This is the ONLY entry point for semantic retrieval.
The offline_responder and patient_agent both call this.
"""

import logging
from typing import List, Optional, Dict, Any

from ai.embedding_service import EmbeddingService
from ai.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Singletons — shared across all agent instances in the same process
_EMB_SVC: Optional[EmbeddingService] = None
_VEC_STORE: Optional[VectorStore] = None


def _get_services():
    global _EMB_SVC, _VEC_STORE
    if _EMB_SVC is None:
        _EMB_SVC = EmbeddingService()
    if _VEC_STORE is None:
        _VEC_STORE = VectorStore()
    return _EMB_SVC, _VEC_STORE


# ── Semantic query expansion ───────────────────────────────────────────────────
# Maps student question intents to additional search terms.
# This improves recall for paraphrasings without changing the core case facts.

_SEMANTIC_EXPANSIONS: Dict[str, List[str]] = {
    "photophobia": [
        "sensitive to light",
        "bright light worsens headache",
        "light sensitivity",
        "photosensitivity",
        "sunlight aggravates",
    ],
    "onset": [
        "when did it start",
        "how long ago did it begin",
        "symptom onset",
        "when did this happen",
    ],
    "location": [
        "where does it hurt",
        "which part is painful",
        "one side headache",
        "pain location",
    ],
    "radiation": [
        "pain spreading",
        "radiates to arm",
        "goes to jaw",
        "shooting pain",
    ],
    "allergy": [
        "allergic reaction",
        "cannot take",
        "medication allergy",
        "penicillin allergy",
    ],
    "medications": [
        "regular medicine",
        "what pills",
        "prescribed drug",
        "taking treatment",
    ],
}


_TOPIC_TO_FACT_TYPE = {
    "medications": ["medications", "past_medical_history"],
    "past_medical": ["past_medical_history", "history_of_illness"],
    "past_history": ["past_medical_history", "history_of_illness"],
    "allergies": ["allergies", "past_medical_history"],
    "family_history": ["family_history"],
    "smoking": ["smoking", "social_history"],
    "alcohol": ["alcohol", "social_history"],
    "drugs": ["social_history"],
    "diet": ["social_history"],
    "exercise": ["social_history"],
    "occupation": ["social_history", "personality"],
    "symptoms": ["symptom", "chief_complaint", "associated_symptoms"],
    "onset_trigger": ["onset", "history_of_illness", "chief_complaint", "symptom"],
    "duration": ["onset", "history_of_illness", "chief_complaint", "symptom"],
    "location_site": ["chief_complaint", "symptom", "radiation"],
    "character_quality": ["character", "symptom", "severity"],
    "radiation": ["radiation", "symptom"],
    "severity": ["severity", "symptom"],
    "associated_symptoms": ["associated_symptoms", "review_of_systems", "symptom"],
}

class SemanticRetriever:
    """
    Usage:
        retriever = SemanticRetriever()
        facts = retriever.retrieve(
            question="Does bright light make it worse?",
            case_id="migraine_001",
            top_k=5,
        )
    """

    # User Request 6: "The system must reject low-confidence retrievals."
    # 0.35 provides a safer threshold than 0.30 for rejecting unrelated clinical inquiries.
    THRESHOLD = 0.30

    def __init__(self):
        self._emb, self._store = _get_services()

    def retrieve(
        self,
        question: str,
        case_id: str,
        top_k: int = 5,
        threshold: Optional[float] = None,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Embed the question, search the vector store (case-isolated), return facts.
        Uses topic to dynamically prioritize fact types.
        """
        if not question or not case_id:
            return []

        t = threshold if threshold is not None else self.THRESHOLD

        try:
            q_vec = self._emb.embed(question)
            # Fetch with a lower threshold to allow topic-based boosting to save marginal but relevant facts
            base_t = t - 0.15 if topic else t
            results = self._store.search(q_vec, case_id=case_id, top_k=top_k * 2, threshold=base_t)
        except Exception as e:
            logger.warning("[SemanticRetriever] Vector search failed: %s", e)
            return []
            
        allowed_types = _TOPIC_TO_FACT_TYPE.get(topic, []) if topic else []
        
        # Metadata / Topic filtering logic
        final_results = []
        for r in results:
            # If we know the topic confidently, prefer those fact types in ranking
            if allowed_types:
                if any(t in r["fact_type"] for t in allowed_types):
                    r["score"] += 0.15  # Boost score natively
            
            if r["score"] >= t:
                final_results.append(r)
            
        final_results.sort(key=lambda x: x["score"], reverse=True)
        return final_results[:top_k]

    def retrieve_texts(
        self,
        question: str,
        case_id: str,
        top_k: int = 5,
        threshold: Optional[float] = None,
        topic: Optional[str] = None
    ) -> List[str]:
        results = self.retrieve(question, case_id, top_k=top_k, threshold=threshold, topic=topic)
        return [r["text"] for r in results]

    def is_unknown_question(
        self,
        question: str,
        case_id: str,
        threshold: Optional[float] = None,
    ) -> bool:
        t = threshold if threshold is not None else self.THRESHOLD
        results = self.retrieve(question, case_id, top_k=1, threshold=t)
        return len(results) == 0

    def build_context_block(
        self,
        question: str,
        case_id: str,
        top_k: int = 6,
        threshold: Optional[float] = None,
    ) -> str:
        """
        Build a formatted context string suitable for prompt injection.
        Returns empty string if nothing found (caller handles fallback).
        """
        results = self.retrieve(question, case_id, top_k=top_k, threshold=threshold)
        if not results:
            return ""

        lines = ["[SEMANTIC CONTEXT — Retrieved patient facts relevant to the student's question]"]
        for r in results:
            lines.append(f"  • [{r['fact_type']}] {r['text']}  (similarity: {r['score']:.2f})")
        return "\n".join(lines)
