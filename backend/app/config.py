from pydantic_settings import BaseSettings
from typing import Optional, List
import os
import json

class Settings(BaseSettings):
    APP_NAME: str = "Burnout Detector API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Audio settings
    MAX_AUDIO_SIZE_MB: int = 50
    ALLOWED_AUDIO_FORMATS: list = ["wav", "mp3", "m4a", "flac"]
    SAMPLE_RATE: int = 16000
    MAX_AUDIO_DURATION_SEC: int = 300
    
    # ML models path
    ML_MODELS_PATH: str = "ml_models"
    
    # Storage settings
    UPLOAD_DIR: str = "uploads"
    TEMP_DIR: str = "temp"
    
    # Cache settings
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # CORS - Read from environment or use defaults
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://razuma.tech",
        "https://www.razuma.tech",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override with environment variable if set
        env_origins = os.getenv("ALLOWED_ORIGINS")
        if env_origins:
            try:
                self.ALLOWED_ORIGINS = json.loads(env_origins)
            except json.JSONDecodeError:
                # If not valid JSON, treat as comma-separated list
                self.ALLOWED_ORIGINS = [origin.strip() for origin in env_origins.split(",")]

settings = Settings()