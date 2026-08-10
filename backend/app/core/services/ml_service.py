import logging
import torch
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path
from transformers import AutoProcessor, AutoModelForAudioClassification
import torchaudio
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.config import settings

logger = logging.getLogger(__name__)

class MLService:
    """
    Сервис для управления ML моделями с локальной загрузкой WavLM
    """
    
    def __init__(self):
        self.models = {}
        self.processors = {}
        self.is_loaded = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # Путь к локальной модели
        self.model_path = Path(settings.ML_MODELS_PATH) / "wavlm-emotion-russian-resd"
        
    async def load_models(self):
        """
        Загрузка всех ML моделей при старте приложения из локальной папки
        """
        try:
            logger.info(f"Loading ML models from {self.model_path} on {self.device}...")
            
            # Диагностика: проверяем, что находится в директории ml_models
            ml_models_path = Path(settings.ML_MODELS_PATH)
            if ml_models_path.exists():
                logger.info(f"Contents of {ml_models_path}:")
                for item in ml_models_path.iterdir():
                    logger.info(f"  - {item.name}")
            else:
                logger.warning(f"Directory {ml_models_path} does not exist")
            
            # Проверяем, существует ли локальная модель
            if not self.model_path.exists():
                logger.error(f"Model not found at {self.model_path}")
                logger.info("Please copy model to: ml_models/wavlm-emotion-russian-resd/")
                logger.info(f"Your current directory: {Path.cwd()}")
                logger.info(f"Absolute path expected: {self.model_path.absolute()}")
                raise FileNotFoundError(f"Model not found at {self.model_path}")
            
            # Проверяем наличие необходимых файлов
            required_files = ['config.json', 'preprocessor_config.json']
            missing_files = []
            for file in required_files:
                if not (self.model_path / file).exists():
                    missing_files.append(file)
            
            if missing_files:
                logger.error(f"Missing required files: {missing_files}")
                logger.info(f"Contents of {self.model_path}:")
                for item in self.model_path.iterdir():
                    logger.info(f"  - {item.name}")
                raise FileNotFoundError(f"Missing files: {missing_files}")
            
            # Загружаем модель из локальной папки
            await self._load_wavlm_model_local()
            
            self.is_loaded = True
            logger.info("✅ All ML models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading ML models: {str(e)}")
            raise
    
    async def _load_wavlm_model_local(self):
        """
        Загрузка модели WavLM из локальной папки
        """
        try:
            model_path = str(self.model_path)
            
            # Загрузка процессора и модели в отдельном потоке
            loop = asyncio.get_event_loop()
            processor, model = await loop.run_in_executor(
                self.executor,
                self._load_wavlm_sync,
                model_path
            )
            
            self.processors['wavlm'] = processor
            self.models['wavlm'] = model
            
            logger.info(f"✅ WavLM model loaded successfully from {model_path}")
            
        except Exception as e:
            logger.error(f"Error loading WavLM model: {str(e)}")
            raise
    
    def _load_wavlm_sync(self, model_path: str):
        """
        Синхронная загрузка модели WavLM из локальной папки
        """
        try:
            logger.info(f"Loading model from {model_path}...")
            
            # Загрузка процессора
            processor = AutoProcessor.from_pretrained(model_path)
            
            # Загрузка модели - БЕЗ device_map='auto'
            model = AutoModelForAudioClassification.from_pretrained(
                model_path
            )
            
            # Явно перемещаем модель на устройство
            model = model.to(self.device)
            model.eval()
            
            # Если используете GPU, можно также использовать torch.compile для ускорения
            if self.device.type == 'cuda':
                logger.info("Model loaded on GPU")
                # model = torch.compile(model)  # Опционально, может ускорить
            else:
                logger.info("Model loaded on CPU")
            
            logger.info(f"Model loaded successfully on {self.device}")
            return processor, model
            
        except Exception as e:
            logger.error(f"Error loading model from {model_path}: {str(e)}")
            raise
    
    async def unload_models(self):
        """
        Выгрузка моделей при остановке приложения
        """
        try:
            self.models.clear()
            self.processors.clear()
            self.is_loaded = False
            logger.info("ML models unloaded")
        except Exception as e:
            logger.error(f"Error unloading models: {str(e)}")
    
    async def predict(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Dict[str, Any]:
        """
        Прогон аудио через модель WavLM для распознавания эмоций
        """
        if not self.is_loaded:
            raise RuntimeError("ML models not loaded")
        
        try:
            results = {}
            wavlm_result = await self._predict_wavlm(audio_data, sample_rate)
            results['wavlm_emotion'] = wavlm_result
            return results
            
        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            raise
    
    async def _predict_wavlm(self, audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """
        Инференс модели WavLM
        """
        try:
            if 'wavlm' not in self.models:
                raise RuntimeError("WavLM model not loaded")
            
            processor = self.processors['wavlm']
            model = self.models['wavlm']
            
            # Преобразование к правильной частоте дискретизации
            if sample_rate != 16000:
                audio_tensor = torch.from_numpy(audio_data).float()
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                audio_tensor = resampler(audio_tensor)
                audio_data = audio_tensor.numpy()
            
            # Подготовка входных данных
            inputs = processor(
                audio_data, 
                sampling_rate=16000, 
                return_tensors="pt",
                padding=True
            )
            
            # Перемещаем тензоры на устройство
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Инференс в отдельном потоке
            loop = asyncio.get_event_loop()
            outputs = await loop.run_in_executor(
                self.executor,
                self._predict_wavlm_sync,
                model,
                inputs
            )
            
            logits = outputs.logits
            probabilities = torch.nn.functional.softmax(logits, dim=-1)
            
            predicted_class_idx = torch.argmax(probabilities, dim=-1).item()
            predicted_prob = probabilities[0][predicted_class_idx].item()
            
            emotion_labels = ['neutral', 'happy', 'sad', 'angry', 'fear', 'disgust', 'surprise']
            predicted_emotion = emotion_labels[predicted_class_idx] if predicted_class_idx < len(emotion_labels) else 'unknown'
            
            all_probabilities = {}
            for idx, label in enumerate(emotion_labels):
                if idx < probabilities.shape[1]:
                    all_probabilities[label] = probabilities[0][idx].item()
            
            return {
                'predicted_emotion': predicted_emotion,
                'confidence': predicted_prob,
                'probabilities': all_probabilities,
                'score': predicted_prob,
                'raw_logits': logits.tolist() if logits is not None else None
            }
            
        except Exception as e:
            logger.error(f"Error in WavLM prediction: {str(e)}")
            raise
    
    def _predict_wavlm_sync(self, model, inputs):
        """
        Синхронный инференс модели (для выполнения в потоке)
        """
        with torch.no_grad():
            outputs = model(**inputs)
        return outputs
    
    async def preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Предобработка аудио перед подачей в модели
        """
        return audio_data
    
    async def postprocess_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Постобработка результатов моделей
        """
        return raw_results