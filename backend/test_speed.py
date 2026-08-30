import time
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import SimulationSession, User, Case
from routes.auth import get_current_user

# Pre-initialize embedding to match app lifespan
from ai.embedding_service import EmbeddingService
print("Initializing embedding service (startup equivalent)...")
EmbeddingService()
print("Done.")

db = SessionLocal()
user = db.query(User).first()
app.dependency_overrides[get_current_user] = lambda: user
client = TestClient(app)

case = db.query(Case).filter(Case.id == 'stroke_001').first() # Explicitly testing the stroke case
if not case:
    print("No case in DB!")
    exit()

print(f"Starting simulation for case {case.id}...")
t0 = time.time()
res_sim = client.post("/api/simulation/start", json={"case_id": case.id})
t1 = time.time()
print(f"Start simulation latency: {(t1 - t0)*1000:.2f} ms")

session_id = res_sim.json().get("id")

print("\nRunning simulated student questions...")
qs = [
    'hello',
    'how are you',
    'what symptoms are you having?',
    'when did the weakness start?',
    'do you have any medical conditions?',
    'are you having chest discomfort?' 
]
from ai.semantic_retriever import SemanticRetriever

for q in qs:
    t0 = time.time()
    res = client.post(f"/api/simulation/{session_id}/question", json={"question": q})
    t1 = time.time()
    data = res.json()
    ans = data.get("answer") or data.get("response", "")
    print(f'\nQ: {q}\nA: {ans}\nLatency: {(t1 - t0)*1000:.2f} ms')
