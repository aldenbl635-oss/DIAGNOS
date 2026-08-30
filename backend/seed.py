from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
import models
from case_engine.engine import case_engine

def seed_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Clear existing cases to load fresh body-part variants
        db.query(models.Case).delete()
        
        # Load and seed cases from CaseEngine JSON
        for case_id, case_data in case_engine.cases.items():
            new_case = models.Case(
                id=case_id,
                title=case_data.get("title"),
                specialty=case_data.get("specialty", "General Medicine"),
                difficulty=case_data.get("difficulty", "Intermediate"),
                duration_mins=case_data.get("duration_mins", 20),
                data=case_data
            )
            db.add(new_case)
            print(f"Seeding case: {case_data.get('title')} ({case_id})")
        db.commit()
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
