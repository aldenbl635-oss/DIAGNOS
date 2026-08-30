from ai.vector_store import VectorStore
store = VectorStore()
print(f"Total facts for stroke_001: {store.count_by_case('stroke_001')}")
for r in store._records:
    if r['case_id'] == 'stroke_001':
        print(f"Fact: {r['fact_type']} | {r['text']}")
