from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from config import settings
from database import engine, Base, migrate_db
from routes import auth, cases, simulation, dashboard

# Initialize database tables on startup
Base.metadata.create_all(bind=engine)
migrate_db()

app = FastAPI(
    title="DiagnOS API",
    description="Backend API for DiagnOS - AI Clinical Reasoning Simulator",
    version="1.0.0"
)

# CORS configuration to support dev local requests
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes under API prefix
app.include_router(auth.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "DiagnOS Clinical reasoning simulator API running successfully.",
        "demo_mode": settings.DEMO_MODE
    }
