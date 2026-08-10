from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class AudioSourceType(str, Enum):
    FILE = "file"
    URL = "url"
    MICROPHONE = "microphone"

class AnalysisType(str, Enum):
    QUICK = "quick"
    DETAILED = "detailed"
    FULL = "full"

class AudioAnalysisRequest(BaseModel):
    """Запрос на анализ аудио"""
    audio_url: Optional[str] = Field(None, description="URL аудио файла")
    source_type: AudioSourceType = Field(default=AudioSourceType.FILE)
    analysis_type: AnalysisType = Field(default=AnalysisType.QUICK)
    user_id: Optional[str] = Field(None, description="ID пользователя")
    session_id: Optional[str] = Field(None, description="ID сессии")
    additional_params: Optional[dict] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "audio_url": "https://example.com/audio.wav",
                "source_type": "url",
                "analysis_type": "detailed",
                "user_id": "user123"
            }
        }

class AudioChunkRequest(BaseModel):
    """Запрос на анализ части аудио"""
    audio_data: bytes = Field(..., description="Бинарные данные аудио")
    sample_rate: int = Field(16000, description="Частота дискретизации")
    chunk_duration: Optional[float] = Field(3.0, description="Длительность чанка в секундах")
    user_id: Optional[str] = None
    session_id: Optional[str] = None
