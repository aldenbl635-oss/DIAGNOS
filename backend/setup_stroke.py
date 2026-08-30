import json
import os
from database import SessionLocal
from models import Case
from ai.index_cases import index_case
from ai.embedding_service import EmbeddingService
from ai.vector_store import VectorStore

stroke = {
    "id": "stroke_001",
    "scenario_type": "neurology",
    "title": "Stroke",
    "difficulty": "easy",
    "presentation": {
        "chief_complaint": "Slurred speech and arm weakness",
        "initial_briefing": "I came in because of my Slurred speech and arm weakness."
    },
    "patient": {
        "name": "Tom",
        "chief_complaint": "Slurred speech and arm weakness",
        "initial_statement": "Hello, doctor... I came in because of my Slurred speech and arm weakness."
    },
    "clinical_state": {
        "symptoms": [
            "Sudden weakness and motor deficit in LEFT ARM and LEFT LEG",
            "Slurred speech"
        ]
    },
    "history": {
        "past_medical_history": [
            "Hypertension",
            "High cholesterol"
        ],
        "family_history": [
            "Grandfather died of stroke"
        ],
        "medications": [
            "Amlodipine", "Atorvastatin", "Aspirin"
        ]
    }
}

path = os.path.join(r"C:\Users\Alden\projects\diagnos\backend\case_engine\cases", "stroke_001.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(stroke, f, indent=4)

db = SessionLocal()
existing = db.query(Case).filter(Case.id == "stroke_001").first()
if not existing:
    db.add(Case(id="stroke_001", title="Stroke", specialty="Neurology", difficulty="Easy", duration_mins=20, data=stroke))
    db.commit()
else:
    existing.data = stroke
    db.commit()

emb = EmbeddingService()
store = VectorStore()
n = index_case(stroke, emb, store)
print(f"Indexed {n} facts for stroke_001")
