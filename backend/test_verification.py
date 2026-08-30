import sys
import logging
logging.disable(logging.CRITICAL)

from ai.semantic_retriever import SemanticRetriever
from ai.offline_responder import OfflinePatientResponder
from ai.patient_state import PatientAgentState

# 1. Semantic Retrieval tests
retriever = SemanticRetriever()
questions = [
    'Does bright light make your chest pain worse?',
    'Are you sensitive to light?',
    'Does sunlight bother you?',
    'Which part of your chest hurts?',
    'Where is the pain concentrated?',
    'When did this begin?',
    'Have you experienced this before?'
]
print('=== SEMANTIC RETRIEVAL TESTS ===')
for q in questions:
    res = retriever.retrieve(q, 'chest_pain_001', top_k=1, threshold=0.1)
    if res:
        print(f'Q: {q}  -->  Score: {res[0]["score"]:.3f} | Fact: {res[0]["text"]}')
    else:
        print(f'Q: {q}  -->  No result')

# 2. Unknown question test
print('\n=== UNKNOWN QUESTION TEST ===')
res_unk = retriever.retrieve('What did you eat for breakfast?', 'chest_pain_001', top_k=1, threshold=0.1)
if res_unk:
    print(f'Score: {res_unk[0]["score"]:.3f} | Text: {res_unk[0]["text"]}')

# Let's test the OfflineResponder directly
responder = OfflinePatientResponder(case_data={"id": "chest_pain_001", "patient": {"name":"Test"}, "clinical_facts":{}})
from ai.patient_memory import PatientMemory
from ai.patient_emotion import EmotionalState
state = PatientAgentState("chest_pain_001", "Test")
state.memory = PatientMemory()
state.emotion = EmotionalState()
com_analysis = {"intent": "clinical_question", "tone": "neutral", "severity": "moderate", "professionalism": "high", "empathetic": "neutral", "reassurance": "none", "dismissive": "none", "alarmist": "none", "threat": "none", "insult": "none", "apology": "none"}

print('\n=== RESPONDER UNKNOWN TEST ===')
resp = responder.respond("What did you eat for breakfast?", state, com_analysis, semantic_facts=[])
print(resp["response"])

print('\n=== RESPONDER UNRELATED TEST ===')
# Test with random bizarre investigations that used to match regex poorly
# By passing semantic_facts=[] it falls back to regex. Let's see what happens.
resp = responder.respond("I am going to order a Duplex Vascular Leg Ultrasound.", state, com_analysis, semantic_facts=[])
print(resp["response"])

