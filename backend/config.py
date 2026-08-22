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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()

# Check if LLM API keys are provided and auto-toggle DEMO_MODE if requested
if not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY:
    settings.DEMO_MODE = True
