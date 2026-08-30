import json
from ai.offline_responder import OfflinePatientResponder, extract_topic
from ai.patient_agent import PatientAgentState
from ai.semantic_retriever import SemanticRetriever

with open('case_engine/cases/migraine_001.json', 'r') as f:
    case_data = json.load(f)
sem = SemanticRetriever()

questions = [
    'Can you describe what the headache feels like?',
    'Does bright light make it worse?',
    'Are you feeling nauseated?',
    'Have you experienced this type of headache before?',
    'What medication do you take for this?',
    'How are you feeling right now?',
]
for q in questions:
    t = extract_topic(q)
    facts = sem.retrieve(q, 'migraine_001', 5, 0.25, t)
    print(f'Q: {q}')
    print(f'  topic={t}')
    for f in facts:
        print(f'  -> {f["text"]} (score={f["score"]:.3f})')
