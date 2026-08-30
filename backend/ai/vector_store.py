"""
VectorStore — in-process vector database for patient facts.

This module acts as the Actian VectorAI integration layer.
All Actian-specific connection code is isolated here.

Architecture:
  EmbeddingService → float32 vectors → VectorStore (Actian) → similarity search

Environment variables (set in backend/.env):
    ACTIAN_HOST         Actian VectorAI host (defaults to localhost)
    ACTIAN_PORT         Port (defaults to 5432)
    ACTIAN_DATABASE     Database name
    ACTIAN_USER         Database user
    ACTIAN_PASSWORD     Database password
    ACTIAN_USE_ACTIAN   Set to "true" to enable Actian; otherwise uses in-memory fallback

When ACTIAN_USE_ACTIAN is not "true" (the default for local dev), the store
uses a fast in-memory NumPy index so the system works offline without any
Actian installation.
"""

import os
import json
import math
import logging
from typing import List, Optional, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

# ── Environment ───────────────────────────────────────────────────────────────

ACTIAN_HOST     = os.getenv("ACTIAN_HOST", "localhost")
ACTIAN_PORT     = int(os.getenv("ACTIAN_PORT", "5432"))
ACTIAN_DATABASE = os.getenv("ACTIAN_DATABASE", "diagnos_vectors")
ACTIAN_USER     = os.getenv("ACTIAN_USER", "")
ACTIAN_PASSWORD = os.getenv("ACTIAN_PASSWORD", "")
USE_ACTIAN      = os.getenv("ACTIAN_USE_ACTIAN", "false").lower() == "true"

VECTOR_DIM = 384  # all-MiniLM-L6-v2 output dimension

# Persistent disk index path (used when Actian is not configured)
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_DISK_INDEX_PATH = os.path.join(_DATA_DIR, "vector_index.json")

# ── Persistent Disk Index (default dev fallback) ──────────────────────────────

class _PersistentDiskIndex:
    """
    JSON flat-file vector store that survives process restarts.
    All reads and writes go through the same file: data/vector_index.json.
    Used when Actian VectorAI is NOT configured.
    """

    def __init__(self, path: str = _DISK_INDEX_PATH):
        self._path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._records: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._records = json.load(f)
                logger.info(
                    "[VectorStore] Loaded %d vectors from disk (%s)",
                    len(self._records),
                    self._path,
                )
            except Exception as e:
                logger.warning("[VectorStore] Could not load disk index: %s", e)
                self._records = []
        else:
            self._records = []

    def _save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._records, f)
        except Exception as e:
            logger.error("[VectorStore] Could not save disk index: %s", e)

    def upsert(
        self,
        embedding: np.ndarray,
        case_id: str,
        fact_type: str,
        fact_key: str,
        source: str,
        text: str,
    ) -> None:
        for rec in self._records:
            if rec["case_id"] == case_id and rec["fact_key"] == fact_key:
                rec["embedding"] = embedding.tolist()
                rec["fact_type"] = fact_type
                rec["source"] = source
                rec["text"] = text
                self._save()
                return
        self._records.append(
            {
                "embedding": embedding.tolist(),
                "case_id": case_id,
                "fact_type": fact_type,
                "fact_key": fact_key,
                "source": source,
                "text": text,
            }
        )
        self._save()

    def search(
        self,
        query_vec: np.ndarray,
        case_id: str,
        top_k: int = 5,
        threshold: float = 0.30,
    ) -> List[Dict[str, Any]]:
        """
        CASE-ISOLATED search: only returns records whose case_id matches.
        Cross-case leakage is NEVER permitted.
        """
        q = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []

        results = []
        for rec in self._records:
            if rec["case_id"] != case_id:  # HARD CASE ISOLATION
                continue
            vec = np.array(rec["embedding"], dtype=np.float32)
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                continue
            score = float(np.dot(q, vec) / (q_norm * vec_norm))
            if score >= threshold:
                results.append(
                    {
                        "text": rec["text"],
                        "fact_type": rec["fact_type"],
                        "fact_key": rec["fact_key"],
                        "source": rec["source"],
                        "score": score,
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def delete_case(self, case_id: str) -> int:
        before = len(self._records)
        self._records = [r for r in self._records if r["case_id"] != case_id]
        self._save()
        return before - len(self._records)

    def count(self) -> int:
        return len(self._records)

    def count_by_case(self, case_id: str) -> int:
        return sum(1 for r in self._records if r["case_id"] == case_id)


# ── Actian VectorAI Backend ───────────────────────────────────────────────────

class _ActianBackend:
    """
    Actian VectorAI integration using psycopg2 (PostgreSQL-compatible wire).

    Schema (auto-created):
        CREATE TABLE patient_facts (
            id          SERIAL PRIMARY KEY,
            case_id     VARCHAR(128) NOT NULL,
            fact_type   VARCHAR(64),
            fact_key    VARCHAR(256),
            source      VARCHAR(64),
            text        TEXT,
            embedding   TEXT,          -- JSON float array
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(case_id, fact_key)
        );
    """

    def __init__(self):
        self._conn = None
        self._connect()
        self._ensure_schema()

    def _connect(self):
        try:
            import psycopg2
            self._conn = psycopg2.connect(
                host=ACTIAN_HOST,
                port=ACTIAN_PORT,
                dbname=ACTIAN_DATABASE,
                user=ACTIAN_USER,
                password=ACTIAN_PASSWORD,
            )
            self._conn.autocommit = True
            logger.info("[VectorStore] Connected to Actian VectorAI at %s:%s/%s", ACTIAN_HOST, ACTIAN_PORT, ACTIAN_DATABASE)
        except Exception as e:
            logger.error("[VectorStore] Actian connection failed: %s", e)
            raise

    def _ensure_schema(self):
        with self._conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS patient_facts (
                    id          SERIAL PRIMARY KEY,
                    case_id     VARCHAR(128) NOT NULL,
                    fact_type   VARCHAR(64),
                    fact_key    VARCHAR(256),
                    source      VARCHAR(64),
                    text        TEXT,
                    embedding   TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(case_id, fact_key)
                )
            """)

    def upsert(self, embedding, case_id, fact_type, fact_key, source, text):
        vec_json = json.dumps(embedding.tolist())
        with self._conn.cursor() as cur:
            cur.execute("""
                INSERT INTO patient_facts (case_id, fact_type, fact_key, source, text, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (case_id, fact_key)
                DO UPDATE SET
                    fact_type = EXCLUDED.fact_type,
                    source    = EXCLUDED.source,
                    text      = EXCLUDED.text,
                    embedding = EXCLUDED.embedding
            """, (case_id, fact_type, fact_key, source, text, vec_json))

    def search(self, query_vec, case_id, top_k=5, threshold=0.30):
        # Fetch all rows for this case, compute cosine in Python
        # (For production, use pgvector or Actian's native vector similarity)
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT text, fact_type, fact_key, source, embedding FROM patient_facts WHERE case_id = %s",
                (case_id,)
            )
            rows = cur.fetchall()

        q = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []

        results = []
        for text, fact_type, fact_key, source, emb_json in rows:
            vec = np.array(json.loads(emb_json), dtype=np.float32)
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                continue
            score = float(np.dot(q, vec) / (q_norm * vec_norm))
            if score >= threshold:
                results.append({"text": text, "fact_type": fact_type, "fact_key": fact_key, "source": source, "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def delete_case(self, case_id):
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM patient_facts WHERE case_id = %s", (case_id,))
            return cur.rowcount

    def count_by_case(self, case_id):
        with self._conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM patient_facts WHERE case_id = %s", (case_id,))
            return cur.fetchone()[0]

    def count(self):
        with self._conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM patient_facts")
            return cur.fetchone()[0]


# ── VectorStore public facade ─────────────────────────────────────────────────

_STORE_INSTANCE = None


def get_vector_store() -> "_PersistentDiskIndex | _ActianBackend":
    """Return singleton vector store (Actian or persistent disk)."""
    global _STORE_INSTANCE
    if _STORE_INSTANCE is None:
        if USE_ACTIAN:
            try:
                _STORE_INSTANCE = _ActianBackend()
                print("[DIAGNOS AI] Vector backend: Actian VectorAI")
                logger.info("[VectorStore] Using Actian VectorAI backend.")
            except Exception as e:
                logger.warning("[VectorStore] Actian unavailable (%s), falling back to persistent disk index.", e)
                _STORE_INSTANCE = _PersistentDiskIndex()
                print(f"[DIAGNOS AI] Vector backend: Local persistent disk (Actian failed: {e})")
        else:
            _STORE_INSTANCE = _PersistentDiskIndex()
            print(f"[DIAGNOS AI] Vector backend: Local persistent disk ({_DISK_INDEX_PATH})")
            logger.info("[VectorStore] Using persistent disk index at %s", _DISK_INDEX_PATH)
    return _STORE_INSTANCE


class VectorStore:
    """
    Public interface. Import this class everywhere; backend is swappable.
    """

    def __init__(self):
        self._store = get_vector_store()

    def upsert(
        self,
        embedding: np.ndarray,
        case_id: str,
        fact_type: str,
        fact_key: str,
        source: str,
        text: str,
    ) -> None:
        """Insert or update a single fact vector."""
        self._store.upsert(embedding, case_id, fact_type, fact_key, source, text)

    def search(
        self,
        query_vec: np.ndarray,
        case_id: str,
        top_k: int = 5,
        threshold: float = 0.30,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search restricted to case_id.
        Returns list of {"text", "fact_type", "fact_key", "source", "score"}.
        Cross-case results are never returned.
        """
        return self._store.search(query_vec, case_id, top_k=top_k, threshold=threshold)

    def delete_case(self, case_id: str) -> int:
        """Delete all vectors for a case. Returns number of deleted rows."""
        return self._store.delete_case(case_id)

    def count_by_case(self, case_id: str) -> int:
        """Count how many vectors are indexed for a case."""
        return self._store.count_by_case(case_id)

    def total_count(self) -> int:
        return self._store.count()
