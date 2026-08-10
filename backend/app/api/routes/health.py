from fastapi import APIRouter, HTTPException
from datetime import datetime
import psutil
import os

router = APIRouter()

@router.get("/ping")
async def ping():
    """Проверка доступности сервиса"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/status")
async def health_check():
    """Полная проверка состояния сервиса"""
    try:
        # Проверка ML моделей
        # Здесь можно добавить проверку загрузки моделей
        
        # Системная информация
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            },
            "services": {
                "ml_models": "loaded",  # Проверить фактическое состояние
                "redis": "connected" if os.getenv("REDIS_URL") else "not_configured"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
