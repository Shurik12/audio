# Модели для API
from .request_models import (
    AudioAnalysisRequest,
    AudioChunkRequest,
    AudioSourceType,
    AnalysisType
)

from .response_models import (
    AudioAnalysisResponse,
    BurnoutResult,
    BurnoutLevel,
    ProcessingStatus,
    AudioFeatures,
    ModelResult
)

__all__ = [
    'AudioAnalysisRequest',
    'AudioChunkRequest',
    'AudioSourceType',
    'AnalysisType',
    'AudioAnalysisResponse',
    'BurnoutResult',
    'BurnoutLevel',
    'ProcessingStatus',
    'AudioFeatures',
    'ModelResult'
]
