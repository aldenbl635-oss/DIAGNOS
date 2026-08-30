import json
import os
from database import SessionLocal
from models import Case
from ai.index_cases import index_case
from ai.embedding_service import EmbeddingService
from ai.vector_store import VectorStore

migraine = {
    "id": "migraine_001",
    "scenario_type": "neurology",
    "title": "Migraine",
    "difficulty": "easy",
    "presentation": {
        "chief_complaint": "terrible headache",
        "initial_briefing": "I've had this terrible headache for about 30 minutes, and the light is really bothering me."
    },
    "patient": {
        "name": "Carol",
        "chief_complaint": "terrible headache",
        "initial_statement": "Hello doctor... I've had this terrible headache for about 30 minutes, and the light is really bothering me."
    },
    "clinical_state": {
        "symptoms": [
            "Right-sided headache / behind right eye and temple",
            "Photophobia",
            "Nausea"
        ]
    },
    "history": {
        "past_medical_history": [
            "History of similar migraine headaches"
        ],
        "medications": [
            "Sumatriptan 50mg as needed for migraine onset"
        ]
    }
}

path = os.path.join(r"C:\Users\Alden\projects\diagnos\backend\case_engine\cases", "migraine_001.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(migraine, f, indent=4)

db = SessionLocal()
existing = db.query(Case).filter(Case.id == "migraine_001").first()
if not existing:
    db.add(Case(id="migraine_001", title="Migraine", specialty="Neurology", difficulty="Easy", duration_mins=20, data=migraine))
    db.commit()
else:
    existing.data = migraine
    db.commit()

emb = EmbeddingService()
store = VectorStore()
n = index_case(migraine, emb, store)
print(f"Indexed {n} facts for migraine_001")
