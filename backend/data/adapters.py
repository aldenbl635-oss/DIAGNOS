import os
import json
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

class DialogueDatasetAdapter:
    """Adapter for MedDialog/NoteChat medical dialogue datasets."""
    def __init__(self):
        self.directory = os.path.join(DATA_DIR, "dialogue")
        os.makedirs(self.directory, exist_ok=True)
        self.is_connected = any(
            os.path.exists(os.path.join(self.directory, f))
            for f in os.listdir(self.directory)
            if not f.startswith(".")
        ) if os.path.exists(self.directory) else False

    def get_status(self) -> str:
        return "Configured" if self.is_connected else "Not connected"

    def load(self) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
        
        # Load any json dialog formats present
        dialogues = []
        for filename in os.listdir(self.directory):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.directory, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            dialogues.extend(data)
                except Exception as e:
                    print(f"Error loading dialogue file {filename}: {e}")
        return dialogues

    def search(self, query: str) -> List[Dict[str, Any]]:
        dialogues = self.load()
        if not dialogues:
            return []
        
        query_words = query.lower().split()
        matches = []
        for d in dialogues:
            text = (d.get("patient", "") + " " + d.get("doctor", "") + " " + d.get("utterance", "")).lower()
            if any(w in text for w in query_words):
                matches.append(d)
        return matches[:3]

    def retrieve_similar_dialogue(self, query: str) -> str:
        matches = self.search(query)
        if not matches:
            return ""
        
        snippets = []
        for m in matches:
            pat = m.get("patient", m.get("utterance", ""))
            doc = m.get("doctor", "")
            if doc and pat:
                snippets.append(f"Doctor: \"{doc}\"\nPatient: \"{pat}\"")
            elif pat:
                snippets.append(f"Patient description: \"{pat}\"")
        return "\n\n".join(snippets)

    def get_patient_examples(self, symptom_query: str) -> List[str]:
        matches = self.search(symptom_query)
        return [m.get("patient", m.get("utterance", "")) for m in matches if m.get("patient") or m.get("utterance")]

    def get_doctor_question_examples(self, symptom_query: str) -> List[str]:
        matches = self.search(symptom_query)
        return [m.get("doctor", "") for m in matches if m.get("doctor")]


class ClinicalDatasetAdapter:
    """Adapter for medical record datasets like MIMIC-IV, MIMIC-IV-ED, MIMIC-IV-Note."""
    def __init__(self):
        self.directory = os.path.join(DATA_DIR, "clinical")
        os.makedirs(self.directory, exist_ok=True)
        self.is_connected = any(
            os.path.exists(os.path.join(self.directory, f))
            for f in os.listdir(self.directory)
            if not f.startswith(".")
        ) if os.path.exists(self.directory) else False

    def get_status(self) -> str:
        return "Configured" if self.is_connected else "Not connected"

    def load_case_notes(self) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
        notes = []
        for filename in os.listdir(self.directory):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.directory, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            notes.extend(data)
                except Exception as e:
                    print(f"Error loading clinical file {filename}: {e}")
        return notes

    def retrieve_grounding_context(self, category: str, keywords: List[str]) -> str:
        """Fetch matching vitals summaries or note templates for clinical grounding context."""
        if not self.is_connected:
            return ""
        notes = self.load_case_notes()
        matches = []
        for note in notes:
            content = note.get("text", "").lower()
            if any(k.lower() in content for k in keywords):
                matches.append(note.get("text", ""))
        
        if matches:
            return f"\n[Clinical Grounding Context (MIMIC-IV)]\n" + "\n---\n".join(matches[:2])
        return ""


class DecisionMakingAdapter:
    """Adapter for sequential clinical reasoning tasks like MIMIC-IV-Ext clinical decision making."""
    def __init__(self):
        self.directory = os.path.join(DATA_DIR, "decision_making")
        os.makedirs(self.directory, exist_ok=True)
        self.is_connected = any(
            os.path.exists(os.path.join(self.directory, f))
            for f in os.listdir(self.directory)
            if not f.startswith(".")
        ) if os.path.exists(self.directory) else False

    def get_status(self) -> str:
        return "Configured" if self.is_connected else "Not connected"

    def load_pathways(self) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
        pathways = []
        for filename in os.listdir(self.directory):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.directory, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            pathways.extend(data)
                except Exception as e:
                    pass
        return pathways


class SyntheticBehaviorAdapter:
    """Adapter for importing local datasets of synthetic physician-patient interactions."""
    def __init__(self):
        self.directory = os.path.join(DATA_DIR, "patient_behavior")
        os.makedirs(self.directory, exist_ok=True)
        self.is_connected = any(
            os.path.exists(os.path.join(self.directory, f))
            for f in os.listdir(self.directory)
            if not f.startswith(".")
        ) if os.path.exists(self.directory) else False

    def get_status(self) -> str:
        return "Configured" if self.is_connected else "Not connected"

    def load_behavior_examples(self) -> List[Dict[str, Any]]:
        # Check standard synthetic behavior file
        examples_file = os.path.join(self.directory, "synthetic_behaviors.json")
        if os.path.exists(examples_file):
            try:
                with open(examples_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []


# Retrievers definition
class MedicalKnowledgeRetriever:
    """Retrieves relevant patient medications and medical guidelines dynamically."""
    def __init__(self):
        self.clinical_adapter = ClinicalDatasetAdapter()

    def retrieve_guidelines(self, symptoms: List[str], medications: List[str]) -> str:
        keywords = symptoms + medications
        context = self.clinical_adapter.retrieve_grounding_context("symptoms", keywords)
        return context


class DialogueRetriever:
    """Retrieves doctor-patient conversational transcripts from datasets to ground LLM outputs."""
    def __init__(self):
        self.dialogue_adapter = DialogueDatasetAdapter()

    def get_conversational_grounding(self, query: str) -> str:
        context = self.dialogue_adapter.retrieve_similar_dialogue(query)
        if context:
            return f"\n[Medical Dialogue Reference (MedDialog)]\n{context}\n"
        return ""


class ClinicalCaseRetriever:
    """Retrieves similar structured clinical cases to guide simulation reasoning."""
    def __init__(self, current_case_data: Dict[str, Any]):
        self.current_case = current_case_data

    def get_relevant_differential_clues(self) -> List[str]:
        return self.current_case.get("critical_clues", [])
