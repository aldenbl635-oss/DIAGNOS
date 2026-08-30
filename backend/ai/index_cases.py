"""
index_cases.py — Case JSON → Embedding → VectorStore indexer

Run once (or after changing case files):
    cd backend
    venv/Scripts/python -m ai.index_cases

Or import and call index_all_cases() programmatically.

Idempotent: re-indexing a case replaces its old vectors.
Supports re-indexing individual cases when their JSON changes.
Does NOT re-index on every student message.
"""

import os
import json
import glob
import logging
from typing import Dict, Any, List

from ai.embedding_service import EmbeddingService
from ai.vector_store import VectorStore

logger = logging.getLogger(__name__)

CASES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "case_engine", "cases"
)


def _extract_facts(case_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract all indexable facts from a case JSON.
    Returns list of {"fact_type": str, "fact_key": str, "text": str}.
    """
    facts = []
    case_id = case_data.get("id", "unknown")
    clinical = case_data.get("clinical_facts", {})
    history = case_data.get("history", {})
    patient = case_data.get("patient", {})

    def add(fact_type: str, key_suffix: str, text: str):
        if text and text.strip():
            facts.append({
                "fact_type": fact_type,
                "fact_key": f"{case_id}::{fact_type}::{key_suffix}",
                "text": text.strip(),
            })

    # ── Chief complaint ────────────────────────────────────────────────────
    cc = patient.get("chief_complaint") or case_data.get("presentation", {}).get("chief_complaint", "")
    if cc:
        add("chief_complaint", "main", f"Chief complaint: {cc}")
        add("chief_complaint", "initial", patient.get("initial_statement", ""))

    # ── Symptoms ───────────────────────────────────────────────────────────
    symptoms = clinical.get("symptoms") or case_data.get("clinical_state", {}).get("symptoms") or []
    for i, s in enumerate(symptoms):
        add("symptom", f"sym_{i}", str(s))
        add("symptom", f"sym_nl_{i}", f"symptom I am having: {s}")
        
        # Add synonym bridges for known symptom terms so questions like
        # "Are you feeling nauseated?" still retrieve "Nausea"
        sl = str(s).lower().strip()
        if sl in ("nausea", "nauseous") or sl.startswith("nausea"):
            add("symptom", f"sym_nausea_{i}", "feeling nauseated, sick to my stomach, nausea, throwing up, vomiting")
        elif "photophobia" in sl or "light" in sl:
            add("photophobia", f"sym_photo_{i}", "sensitive to light, bright light worsens symptoms, photophobia")
        elif "headache" in sl:
            add("symptom", f"sym_head_{i}", f"headache: {s}")
        elif "weakness" in sl or "paralysis" in sl or "motor deficit" in sl:
            add("symptom", f"sym_weak_{i}", f"weakness, unable to move: {s}")
        elif "speech" in sl or "slurr" in sl:
            add("symptom", f"sym_speech_{i}", f"speech difficulty, slurred speech: {s}")
            
        if any(w in sl for w in ["burn", "crush", "ache", "sharp", "dull", "pressure", "tight", "squeeze", "heavy", "throbbing"]):
            add("character", f"sym_char_{i}", f"the pain feels like: {s}")
    onset = clinical.get("onset") or case_data.get("clinical_state", {}).get("onset", "")
    if onset:
        add("onset", "main", f"Onset (when it started): {onset}")
    for i, h in enumerate(clinical.get("history_of_illness", [])):
        add("history_of_illness", f"hoi_{i}", str(h))

    # ── Pain characteristics ───────────────────────────────────────────────
    for i, s in enumerate(symptoms):
        sl = str(s).lower()
        if any(w in sl for w in ["radiat", "spread", "arm", "jaw", "shoulder", "neck"]):
            add("radiation", f"rad_{i}", str(s))
        if any(w in sl for w in ["severe", "mild", "7/10", "8/10", "9/10", "out of 10"]):
            add("severity", f"sev_{i}", str(s))
        if any(w in sl for w in ["pressure", "crushing", "squeezing", "burning", "sharp", "dull", "aching"]):
            add("character", f"char_{i}", str(s))
        if any(w in sl for w in ["exert", "climb", "walk", "rest", "reliev", "better", "worse"]):
            add("exacerbating_relieving", f"er_{i}", str(s))

    # ── Past medical history ───────────────────────────────────────────────
    pmh = clinical.get("past_medical_history") or history.get("past_medical_history", [])
    for i, p in enumerate(pmh):
        add("past_medical_history", f"pmh_{i}", str(p))
        add("past_medical_history", f"pmh_nl_{i}", f"medical condition / past history: {p}")

    # ── Medications ────────────────────────────────────────────────────────
    meds = clinical.get("medications") or history.get("medications", [])
    for i, m in enumerate(meds):
        add("medications", f"med_{i}", str(m))
        add("medications", f"med_nl_{i}", f"taking medications: {m}")

    # ── Allergies ──────────────────────────────────────────────────────────
    allergies = clinical.get("allergies") or history.get("allergies", [])
    for i, a in enumerate(allergies):
        add("allergies", f"allergy_{i}", str(a))
        add("allergies", f"allergy_nl_{i}", f"allergies to: {a}")

    # ── Family history ─────────────────────────────────────────────────────
    family = clinical.get("family_history") or history.get("family_history", [])
    for i, f in enumerate(family):
        add("family_history", f"fam_{i}", str(f))
        add("family_history", f"fam_nl_{i}", f"family history: {f}")

    # ── Social / lifestyle history ─────────────────────────────────────────
    social = (
        clinical.get("social_history")
        or history.get("social_history")
        or history.get("lifestyle_risk_factors")
        or []
    )
    for i, s in enumerate(social):
        add("social_history", f"soc_{i}", str(s))
        # Bridge common semantic mappings
        sl = str(s).lower()
        if "smok" in sl or "cigarette" in sl:
            add("smoking", f"smk_{i}", str(s))
        if "alcohol" in sl or "drink" in sl or "beer" in sl:
            add("alcohol", f"alc_{i}", str(s))
        if "stress" in sl or "work" in sl:
            add("stress", f"str_{i}", str(s))

    # ── Associated symptoms ────────────────────────────────────────────────
    assoc = clinical.get("associated_symptoms") or case_data.get("clinical_state", {}).get("associated_symptoms", [])
    for i, a in enumerate(assoc):
        add("associated_symptoms", f"assoc_{i}", str(a))

    # ── Review of systems ──────────────────────────────────────────────────
    ros = clinical.get("review_of_systems", [])
    for i, r in enumerate(ros):
        add("review_of_systems", f"ros_{i}", str(r))

    # ── Patient personality (traits affect how to interact) ────────────────
    personality = case_data.get("patient_personality", {})
    if personality:
        add("personality", "summary",
            f"Patient personality: anxiety={personality.get('baseline_anxiety',50)}, "
            f"cooperativeness={personality.get('cooperativeness',65)}, "
            f"health_literacy={personality.get('health_literacy',50)}"
        )

    # ── Photophobia / light sensitivity semantic bridge ────────────────────
    # Ensures "Does bright light make it worse?" maps to photophobia facts
    all_text = " ".join(str(v) for v in symptoms + assoc + ros).lower()
    if any(w in all_text for w in ["light", "photo", "bright", "sun"]):
        add("photophobia", "semantic_bridge",
            "photophobia: sensitive to light, bright light worsens headache, photosensitivity")

    return facts


def index_case(case_data: Dict[str, Any], emb_svc: EmbeddingService, store: VectorStore) -> int:
    """
    Index all facts for a single case. Deletes old vectors first (re-indexing).
    Returns the number of facts indexed.
    """
    case_id = case_data.get("id", "unknown")
    if not case_id or case_id == "unknown":
        logger.warning("Skipping case with no id.")
        return 0

    # Delete existing vectors for this case (makes re-indexing idempotent)
    deleted = store.delete_case(case_id)
    if deleted > 0:
        logger.info("[Indexer] Deleted %d existing vectors for case %s", deleted, case_id)

    facts = _extract_facts(case_data)
    if not facts:
        logger.warning("[Indexer] No facts extracted for case %s", case_id)
        return 0

    texts = [f["text"] for f in facts]
    embeddings = emb_svc.embed_batch(texts)

    for fact, vec in zip(facts, embeddings):
        store.upsert(
            embedding=vec,
            case_id=case_id,
            fact_type=fact["fact_type"],
            fact_key=fact["fact_key"],
            source="case_json",
            text=fact["text"],
        )

    logger.info("[Indexer] Indexed %d facts for case %s", len(facts), case_id)
    return len(facts)


def index_all_cases(cases_dir: str = CASES_DIR) -> Dict[str, int]:
    """
    Read all JSON files in cases_dir, index every case.
    Returns {case_id: fact_count}.
    """
    emb_svc = EmbeddingService()
    store = VectorStore()

    pattern = os.path.join(cases_dir, "*.json")
    files = glob.glob(pattern)
    if not files:
        logger.warning("[Indexer] No case JSON files found in %s", cases_dir)
        return {}

    results = {}
    for path in sorted(files):
        try:
            with open(path, "r", encoding="utf-8") as f:
                case_data = json.load(f)
            count = index_case(case_data, emb_svc, store)
            case_id = case_data.get("id", os.path.basename(path))
            results[case_id] = count
        except Exception as e:
            logger.error("[Indexer] Failed to index %s: %s", path, e)

    total = sum(results.values())
    logger.info("[Indexer] Indexing complete. Total facts: %d across %d cases.", total, len(results))
    print(f"\n[Indexer] Done. Indexed {total} facts across {len(results)} cases.")
    for cid, cnt in results.items():
        print(f"  {cid}: {cnt} facts")
    return results


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    index_all_cases()
