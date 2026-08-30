import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./diagnos.db"
    SECRET_KEY: str = "super_secret_diagnos_key_for_hackathon_demo_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # LLM Settings
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""
    GEMINI_API_KEY: str = ""
    DEMO_MODE: bool = True

    # Hybrid RAG+LLM pipeline controls
    # Set LLM_ENABLED=true in .env to activate the LLM generation tier.
    # If LLM_ENABLED is false, or the LLM call fails/times-out, the
    # OfflinePatientResponder is used as fallback (existing behaviour).
    LLM_ENABLED: bool = False
    LLM_TIMEOUT: float = 8.0      # seconds before falling back to OfflineResponder
    LLM_MODEL_GEMINI: str = "gemini-2.0-flash"
    LLM_MODEL_OPENAI: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3  # low temp for medical accuracy

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()

# Auto-toggle DEMO_MODE and LLM_ENABLED based on key availability
if not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY:
    settings.DEMO_MODE = True
    settings.LLM_ENABLED = False
elif settings.LLM_ENABLED is False:
    # Keys present but LLM explicitly disabled → still enable DEMO_MODE fallback
    settings.DEMO_MODE = True
