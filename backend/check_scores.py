from ai.semantic_retriever import SemanticRetriever
from test_speed import client
from database import SessionLocal
from models import Case
from ai.embedding_service import EmbeddingService
from ai.patient_agent import PatientAgent
case = SessionLocal().query(Case).filter(Case.id=='stroke_001').first()
sr = SemanticRetriever()
from ai.index_cases import index_case
index_case(case.data, EmbeddingService(), sr._store)
print('Total in index:', sr._store.total_count())
qs = ['are you having chest discomfort?']
options = ["symptoms", "onset", "medical_conditions", "associated_symptoms", None]
for q in qs:
    print('\nQuery:', q)
    for topic in options:
        res = sr._store.search(sr._emb.embed(q), 'stroke_001', top_k=20, threshold=0.0)
        print(f' Topic {topic}:')
        for r in res:
            print(f'   {r["score"]:.3f} | {r["text"]}')
        break
