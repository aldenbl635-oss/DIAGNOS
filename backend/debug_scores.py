import sys; sys.path.insert(0, '.')
from ai.embedding_service import EmbeddingService
from ai.vector_store import VectorStore

emb = EmbeddingService()
store = VectorStore()

qs = [
    ('Are you feeling nauseated?', 'migraine_001'),
    ('Have you experienced this type of headache before?', 'migraine_001'),
]

for q, cid in qs:
    vec = emb.embed(q)
    results = store.search(vec, case_id=cid, top_k=10, threshold=0.0)
    print(f'\nQ: {q}')
    for r in results:
        print(f'  {r["score"]:.3f} | {r["fact_type"]:25s} | {r["text"]}')
