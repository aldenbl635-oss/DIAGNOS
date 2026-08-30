"""
index_all_cases.py — Index ALL case JSON files into the persistent disk vector store.

Run this after adding new cases or after clearing the index:
    cd backend
    venv/Scripts/python index_all_cases.py

This is the master indexer for development. It:
  1. Re-indexes every JSON in case_engine/cases/
  2. Also re-indexes any cases in the SQL database
  3. Prints a summary of indexed facts per case
"""
import json
import os
import sys

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai.index_cases import index_all_cases
from ai.vector_store import VectorStore

if __name__ == "__main__":
    print("[Indexer] Starting full-case indexing...")
    store = VectorStore()
    results = index_all_cases()
    total = sum(results.values())
    print(f"\n[Indexer] Done. Total: {total} facts across {len(results)} cases.")
    print(f"[Indexer] Vector store now contains {store.total_count()} vectors total.")
