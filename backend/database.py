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
    if "evaluations" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("evaluations")}
        if "differential_score" not in columns:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE evaluations ADD COLUMN differential_score FLOAT DEFAULT 0"
                ))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
