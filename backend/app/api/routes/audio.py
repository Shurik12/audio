from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request, Query, Form
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List  # <-- Добавьте недостающие импорты
import logging
import os
import aiofiles
from datetime import datetime
import time
import json

from app.models.request_models import AudioAnalysisRequest, AudioChunkRequest
from app.models.response_models import (
    AudioAnalysisResponse,
    BurnoutResult,
    ProcessingStatus
)
from app.core.services.audio_service import AudioService
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=AudioAnalysisResponse)
async def analyze_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: Optional[str] = Query(None, description="ID пользователя"),
    session_id: Optional[str] = Query(None, description="ID сессии")
):
    """
    Анализ аудио на предмет выгорания
    """
    start_time = time.time()
    
    try:
        # 1. Валидация файла
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Проверка расширения
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.ALLOWED_AUDIO_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Allowed: {settings.ALLOWED_AUDIO_FORMATS}"
            )
        
        # Сохранение файла
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        temp_file_path = f"{settings.TEMP_DIR}/{datetime.now().timestamp()}_{file.filename}"
        
        # Проверка размера
        file_size = 0
        async with aiofiles.open(temp_file_path, 'wb') as out_file:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > settings.MAX_AUDIO_SIZE_MB * 1024 * 1024:
                    os.remove(temp_file_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Max size: {settings.MAX_AUDIO_SIZE_MB}MB"
                    )
                await out_file.write(chunk)
        
        # 2. Загрузка аудио
        audio_service = AudioService()
        audio_data = await audio_service.load_audio(
            temp_file_path,
            target_sr=settings.SAMPLE_RATE
        )
        
        # Проверка длительности
        duration = len(audio_data) / settings.SAMPLE_RATE
        if duration > settings.MAX_AUDIO_DURATION_SEC:
            os.remove(temp_file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Audio too long. Max duration: {settings.MAX_AUDIO_DURATION_SEC} seconds"
            )
        
        # 3. Получение ML сервиса
        ml_service = request.app.state.ml_service
        
        # 4. Прогон через модель WavLM
        ml_results = await ml_service.predict(audio_data, settings.SAMPLE_RATE)
        
        # 5. Анализ результатов с передачей аудио для акустических признаков
        result = await audio_service.analyze_results(
            ml_results, 
            audio=audio_data, 
            sr=settings.SAMPLE_RATE
        )
        
        # 6. Очистка временных файлов
        background_tasks.add_task(cleanup_temp_file, temp_file_path)
        
        # 7. Расчет времени обработки
        processing_time = (time.time() - start_time) * 1000
        
        # 8. Формирование ответа
        return AudioAnalysisResponse(
            status=ProcessingStatus.SUCCESS,
            result=result,
            metadata={
                "filename": file.filename,
                "duration_seconds": round(duration, 2),
                "sample_rate": settings.SAMPLE_RATE,
                "user_id": user_id,
                "session_id": session_id,
                "processed_at": datetime.now().isoformat()
            },
            processing_time_ms=round(processing_time, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/analyze-with-baseline",
    summary="Анализ аудио с сравнением с baseline",
    description="""
    Анализирует аудио и сравнивает с baseline пользователя.
    
    **Если baseline не передан, используются значения по умолчанию.**
    
    **Что анализируется:**
    - Эмоциональный профиль (SER)
    - Акустические признаки (pitch, intensity, pauses, speech rate)
    - Динамика изменений относительно baseline
    - Устойчивость паттерна
    
    **Результаты:**
    - State (NORMAL/SHORT_STRESS/SUSTAINED_STRESS/BURNOUT_LIKE/LOW_AFFECT_UNSPECIFIC)
    - Risk (0-100%)
    - Confidence (0-1)
    - Детальные компоненты и рекомендации
    """
)
async def analyze_audio_with_baseline(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Аудиофайл для анализа"),
    baseline_data: Optional[str] = Form(None, description="JSON с данными baseline (опционально)"),
    history_data: Optional[str] = Form(None, description="JSON с историей записей (опционально)"),
    user_id: Optional[str] = Query(None, description="ID пользователя")
):
    """
    Анализ аудио с сравнением с персональным baseline
    """
    start_time = time.time()
    
    try:
        # 1. Валидация файла
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Проверка расширения
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.ALLOWED_AUDIO_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Allowed: {settings.ALLOWED_AUDIO_FORMATS}"
            )
        
        # Сохранение файла
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        temp_file_path = f"{settings.TEMP_DIR}/{datetime.now().timestamp()}_{file.filename}"
        
        # Проверка размера
        file_size = 0
        async with aiofiles.open(temp_file_path, 'wb') as out_file:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > settings.MAX_AUDIO_SIZE_MB * 1024 * 1024:
                    os.remove(temp_file_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Max size: {settings.MAX_AUDIO_SIZE_MB}MB"
                    )
                await out_file.write(chunk)
        
        # 2. Загрузка аудио
        audio_service = AudioService()
        audio_data = await audio_service.load_audio(
            temp_file_path,
            target_sr=settings.SAMPLE_RATE
        )
        
        # Проверка длительности
        duration = len(audio_data) / settings.SAMPLE_RATE
        if duration > settings.MAX_AUDIO_DURATION_SEC:
            os.remove(temp_file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Audio too long. Max duration: {settings.MAX_AUDIO_DURATION_SEC} seconds"
            )
        
        # 3. Получение ML сервиса
        ml_service = request.app.state.ml_service
        
        # 4. Прогон через модель WavLM
        ml_results = await ml_service.predict(audio_data, settings.SAMPLE_RATE)
        
        # 5. Сбор текущего результата
        current_result = await audio_service.analyze_results(ml_results)
        current_result_dict = current_result.dict()
        
        # 6. Получение baseline (если передан) или использование дефолтного
        baseline = None
        history = []
        
        # Функция для получения дефолтного baseline
        def get_default_baseline() -> Dict[str, Any]:
            """Возвращает значения baseline по умолчанию"""
            return {
                'acoustic_features': {
                    'pitch_variation': 0.19,
                    'pitch_range': 60.0,
                    'intensity_variation': 0.3,
                    'pause_ratio': 0.15,
                    'pause_mean_duration': 0.05,
                    'pause_max_duration': 0.10,
                    'speech_rate': 3.5
                },
                'detailed_analysis': {
                    'wavlm_emotion_probabilities': {
                        'neutral': 0.2,
                        'happy': 0.3,
                        'sad': 0.1,
                        'angry': 0.05,
                        'fear': 0.05,
                        'disgust': 0.03,
                        'surprise': 0.05
                    }
                },
                'model_results': [
                    {
                        'all_probabilities': {
                            'neutral': 0.2,
                            'happy': 0.3,
                            'sad': 0.1,
                            'angry': 0.05,
                            'fear': 0.05,
                            'disgust': 0.03,
                            'surprise': 0.05
                        }
                    }
                ]
            }
        
        # Парсинг baseline
        if baseline_data and baseline_data.strip():
            try:
                baseline = json.loads(baseline_data)
                logger.info(f"Baseline loaded from input: {baseline.keys() if baseline else 'None'}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse baseline_data: {e}. Using default baseline.")
                baseline = None
        
        # Если baseline не загружен, используем дефолтный
        if not baseline:
            logger.info("Using default baseline values")
            baseline = get_default_baseline()
            baseline_reliability = 0.5
        else:
            baseline_reliability = 0.7
            
            # Проверяем и дополняем недостающие поля
            if 'acoustic_features' not in baseline:
                baseline['acoustic_features'] = {
                    'pitch_variation': 0.19,
                    'pitch_range': 60.0,
                    'intensity_variation': 0.3,
                    'pause_ratio': 0.15,
                    'pause_mean_duration': 0.05,
                    'pause_max_duration': 0.10,
                    'speech_rate': 3.5
                }
            
            if 'detailed_analysis' not in baseline:
                baseline['detailed_analysis'] = {
                    'wavlm_emotion_probabilities': {
                        'neutral': 0.2,
                        'happy': 0.3,
                        'sad': 0.1,
                        'angry': 0.05,
                        'fear': 0.05,
                        'disgust': 0.03,
                        'surprise': 0.05
                    }
                }
            
            if 'model_results' not in baseline:
                baseline['model_results'] = [
                    {
                        'all_probabilities': baseline['detailed_analysis'].get('wavlm_emotion_probabilities', {})
                    }
                ]
        
        # Парсинг истории
        if history_data and history_data.strip():
            try:
                history = json.loads(history_data)
                if not isinstance(history, list):
                    history = [history]
                logger.info(f"History loaded: {len(history)} records")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse history_data: {e}")
                history = []
        
        # 7. Извлечение окон для анализа динамики
        # В будущем здесь нужно разделить аудио на 5-секундные окна
        windows = []
        
        # 8. Выполнение анализа с использованием алгоритма
        analysis_result = await audio_service.analyze_with_burnout_algorithm(
            current_result=current_result_dict,
            baseline_result=baseline,
            history=history,
            audio_quality=0.8,
            baseline_reliability=baseline_reliability
        )
        
        # 9. Очистка временных файлов
        background_tasks.add_task(cleanup_temp_file, temp_file_path)
        
        # 10. Расчет времени обработки
        processing_time = (time.time() - start_time) * 1000
        
        # 11. Формирование ответа
        return {
            "status": "success",
            "analysis": analysis_result,
            "current_result": current_result_dict,
            "baseline_used": baseline,
            "metadata": {
                "filename": file.filename,
                "duration_seconds": round(duration, 2),
                "user_id": user_id,
                "processed_at": datetime.now().isoformat()
            },
            "processing_time_ms": round(processing_time, 2)
        }
        
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON format in baseline_data or history_data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error in baseline analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-with-params", response_model=AudioAnalysisResponse)
async def analyze_audio_with_params(
    request: Request,
    background_tasks: BackgroundTasks,
    analysis_request: AudioAnalysisRequest
):
    """
    Анализ аудио с дополнительными параметрами
    """
    return AudioAnalysisResponse(
        status=ProcessingStatus.SUCCESS,
        metadata={
            "message": "Not implemented yet",
            "request": analysis_request.dict()
        }
    )


async def cleanup_temp_file(file_path: str):
    """Очистка временного файла"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up temp file: {str(e)}")


@router.get("/status/{task_id}")
async def get_analysis_status(task_id: str):
    """
    Получение статуса асинхронного анализа (если используется Celery)
    """
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Not implemented yet"
    }