from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

class BurnoutLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"

class AudioFeatures(BaseModel):
    """Извлеченные аудио-признаки"""
    mfcc_mean: List[float]
    mfcc_var: List[float]
    spectral_centroid: float
    spectral_bandwidth: float
    spectral_rolloff: float
    zero_crossing_rate: float
    energy: float
    tempo: Optional[float] = None

class ModelResult(BaseModel):
    """Результат отдельной ML модели"""
    model_name: str
    score: float
    confidence: float
    prediction: Optional[str] = None
    all_probabilities: Optional[Dict[str, float]] = None  # <-- ДОБАВЛЕНО

class BurnoutResult(BaseModel):
    """Итоговый результат анализа"""
    level: BurnoutLevel
    score: float  # 0-100
    confidence: float  # 0-1
    recommendations: List[str]
    model_results: List[ModelResult]
    detailed_analysis: Optional[Dict[str, Any]] = None

class AudioAnalysisResponse(BaseModel):
    """Ответ на запрос анализа"""
    status: ProcessingStatus
    result: Optional[BurnoutResult] = None
    metadata: Dict[str, Any]
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None