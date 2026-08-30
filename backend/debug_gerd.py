import json
from ai.semantic_retriever import SemanticRetriever
from ai.offline_responder import extract_topic

sem = SemanticRetriever()

q = "Can you describe what the pain feels like?"
t = extract_topic(q)
print(f"topic: {t}")
facts = sem.retrieve(q, 'chest_pain_003', 5, 0.20, t)
for f in facts:
    print(f'  [{f["fact_type"]}] score={f["score"]:.3f} -> {f["text"]}')
