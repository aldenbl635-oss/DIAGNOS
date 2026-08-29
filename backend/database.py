from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

# In SQLite we need connect_args={"check_same_thread": False} for multi-thread requests
engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def migrate_db():
    """Apply lightweight schema migrations for existing SQLite databases."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    if "evaluations" in table_names:
        eval_cols = {col["name"] for col in inspector.get_columns("evaluations")}
        with engine.begin() as conn:
            if "differential_score" not in eval_cols:
                conn.execute(text("ALTER TABLE evaluations ADD COLUMN differential_score FLOAT DEFAULT 0"))
            if "disposition_score" not in eval_cols:
                conn.execute(text("ALTER TABLE evaluations ADD COLUMN disposition_score FLOAT DEFAULT 0"))
            if "disposition_correct" not in eval_cols:
                conn.execute(text("ALTER TABLE evaluations ADD COLUMN disposition_correct TEXT"))
            if "disposition_expected" not in eval_cols:
                conn.execute(text("ALTER TABLE evaluations ADD COLUMN disposition_expected TEXT"))

    if "simulation_sessions" in table_names:
        session_cols = {col["name"] for col in inspector.get_columns("simulation_sessions")}
        with engine.begin() as conn:
            if "facility_tier" not in session_cols:
                conn.execute(text("ALTER TABLE simulation_sessions ADD COLUMN facility_tier TEXT DEFAULT 'tertiary'"))
            if "disposition" not in session_cols:
                conn.execute(text("ALTER TABLE simulation_sessions ADD COLUMN disposition TEXT"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
