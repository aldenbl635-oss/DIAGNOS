import sys; sys.path.insert(0, '.')
from ai.embedding_service import EmbeddingService
from ai.vector_store import VectorStore

emb = EmbeddingService()
store = VectorStore()

for q, cid in [
    ('Are you feeling nauseated?', 'migraine_001'),
    ('Have you experienced this type of headache before?', 'migraine_001'),
]:
    vec = emb.embed(q)
    results = store.search(vec, case_id=cid, top_k=10, threshold=0.0)
    print(f'Q: {q}')
    for r in results:
        ft = r["fact_type"]
        sc = r["score"]
        tx = r["text"]
        print(f'  {sc:.3f} | {ft:25s} | {tx}')
    print()
