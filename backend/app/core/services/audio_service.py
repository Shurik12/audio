import numpy as np
import librosa
import logging
from typing import Dict, Any, Tuple, Optional, List
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.models.response_models import BurnoutResult, BurnoutLevel, ModelResult
from app.core.services.burnout_analyzer import BurnoutAnalyzer, State
from app.config import settings

logger = logging.getLogger(__name__)

class AudioService:
    """
    Сервис для обработки аудио и извлечения признаков
    """
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def load_audio(
        self, 
        file_path: str, 
        target_sr: int = 16000,
        duration: Optional[float] = None
    ) -> np.ndarray:
        """
        Загрузка и ресемплинг аудиофайла
        """
        try:
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                self.executor,
                self._load_audio_sync,
                file_path,
                target_sr,
                duration
            )
            return audio_data
            
        except Exception as e:
            logger.error(f"Error loading audio: {str(e)}")
            raise
    
    def _load_audio_sync(
        self,
        file_path: str,
        target_sr: int,
        duration: Optional[float] = None
    ) -> np.ndarray:
        """
        Синхронная загрузка аудио (для выполнения в потоке)
        """
        try:
            audio, sr = librosa.load(
                file_path,
                sr=target_sr,
                duration=duration,
                mono=True
            )
            return audio
        except Exception as e:
            logger.error(f"Error in sync audio loading: {str(e)}")
            raise
    
    async def extract_features(self, audio: np.ndarray) -> np.ndarray:
        """
        Извлечение признаков из аудио
        """
        try:
            loop = asyncio.get_event_loop()
            features = await loop.run_in_executor(
                self.executor,
                self._extract_features_sync,
                audio
            )
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            raise
    
    def _extract_features_sync(self, audio: np.ndarray) -> np.ndarray:
        """
        Синхронное извлечение признаков (для выполнения в потоке)
        """
        try:
            features = {}
            
            # MFCC
            mfccs = librosa.feature.mfcc(
                y=audio, 
                sr=settings.SAMPLE_RATE,
                n_mfcc=13
            )
            features['mfcc_mean'] = np.mean(mfccs, axis=1)
            features['mfcc_var'] = np.var(mfccs, axis=1)
            
            # Спектральные признаки
            spectral_centroids = librosa.feature.spectral_centroid(
                y=audio,
                sr=settings.SAMPLE_RATE
            )
            features['spectral_centroid'] = np.mean(spectral_centroids)
            
            spectral_bandwidth = librosa.feature.spectral_bandwidth(
                y=audio,
                sr=settings.SAMPLE_RATE
            )
            features['spectral_bandwidth'] = np.mean(spectral_bandwidth)
            
            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=audio,
                sr=settings.SAMPLE_RATE
            )
            features['spectral_rolloff'] = np.mean(spectral_rolloff)
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(audio)
            features['zero_crossing_rate'] = np.mean(zcr)
            
            # Energy
            features['energy'] = np.sum(audio**2) / len(audio)
            
            # Tempo
            tempo, _ = librosa.beat.beat_track(
                y=audio,
                sr=settings.SAMPLE_RATE
            )
            features['tempo'] = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
            
            # Преобразование в массив numpy
            feature_vectors = []
            feature_vectors.append(features['mfcc_mean'])
            feature_vectors.append(features['mfcc_var'])
            feature_vectors.append(np.array([features['spectral_centroid']]))
            feature_vectors.append(np.array([features['spectral_bandwidth']]))
            feature_vectors.append(np.array([features['spectral_rolloff']]))
            feature_vectors.append(np.array([features['zero_crossing_rate']]))
            feature_vectors.append(np.array([features['energy']]))
            feature_vectors.append(np.array([features['tempo']]))
            
            feature_vector = np.concatenate(feature_vectors)
            return feature_vector
            
        except Exception as e:
            logger.error(f"Error in sync feature extraction: {str(e)}")
            raise
    
    def _round_dict_values(self, d: Dict[str, float], decimals: int = 2) -> Dict[str, float]:
        """
        Округление всех значений в словаре до указанного количества знаков
        """
        return {k: round(v, decimals) for k, v in d.items()}
    
    def _round_value(self, value: float, decimals: int = 2) -> float:
        """
        Округление одного значения
        """
        return round(value, decimals)
    
    def _calculate_pitch_features(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Расчет параметров высоты голоса (Pitch/F0)
        """
        try:
            # Извлечение F0
            f0, voiced_flag, voiced_probs = librosa.pyin(
                audio,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'),
                sr=sr
            )
            
            # Убираем NaN значения
            f0_valid = f0[~np.isnan(f0)]
            
            if len(f0_valid) == 0:
                return {
                    'pitch_mean': 0,
                    'pitch_std': 0,
                    'pitch_range': 0,
                    'pitch_min': 0,
                    'pitch_max': 0,
                    'pitch_variation': 0
                }
            
            # Основные статистики
            pitch_mean = np.mean(f0_valid)
            pitch_std = np.std(f0_valid)
            pitch_min = np.min(f0_valid)
            pitch_max = np.max(f0_valid)
            pitch_range = pitch_max - pitch_min
            
            # Относительная вариативность (коэффициент вариации)
            pitch_variation = pitch_std / pitch_mean if pitch_mean > 0 else 0
            
            return {
                'pitch_mean': float(pitch_mean),
                'pitch_std': float(pitch_std),
                'pitch_range': float(pitch_range),
                'pitch_min': float(pitch_min),
                'pitch_max': float(pitch_max),
                'pitch_variation': float(pitch_variation)
            }
            
        except Exception as e:
            logger.error(f"Error calculating pitch features: {str(e)}")
            return {
                'pitch_mean': 0,
                'pitch_std': 0,
                'pitch_range': 0,
                'pitch_min': 0,
                'pitch_max': 0,
                'pitch_variation': 0
            }
    
    def _calculate_intensity_features(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Расчет параметров интенсивности/громкости
        """
        try:
            # Извлечение RMS энергии
            rms = librosa.feature.rms(y=audio)[0]
            
            # Извлечение огибающей
            envelope = np.abs(librosa.stft(audio))
            intensity = np.mean(envelope, axis=0)
            
            # Основные статистики
            rms_mean = np.mean(rms)
            rms_std = np.std(rms)
            rms_min = np.min(rms)
            rms_max = np.max(rms)
            
            # Относительная вариативность
            intensity_variation = rms_std / rms_mean if rms_mean > 0 else 0
            
            # Динамический диапазон
            dynamic_range = rms_max - rms_min if rms_max > rms_min else 0
            
            return {
                'intensity_mean': float(rms_mean),
                'intensity_std': float(rms_std),
                'intensity_min': float(rms_min),
                'intensity_max': float(rms_max),
                'intensity_variation': float(intensity_variation),
                'dynamic_range': float(dynamic_range)
            }
            
        except Exception as e:
            logger.error(f"Error calculating intensity features: {str(e)}")
            return {
                'intensity_mean': 0,
                'intensity_std': 0,
                'intensity_min': 0,
                'intensity_max': 0,
                'intensity_variation': 0,
                'dynamic_range': 0
            }
    
    def _calculate_speech_rate(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Расчет темпа речи
        """
        try:
            # Определение голосовых сегментов
            # Используем RMS для определения активности
            frame_length = int(0.025 * sr)  # 25ms
            hop_length = int(0.010 * sr)    # 10ms
            rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Порог для определения речи
            threshold = np.mean(rms) * 0.3
            voiced_frames = rms > threshold
            
            # Подсчет переходов между голосовыми и неголосовыми сегментами
            transitions = np.diff(voiced_frames.astype(int))
            
            # Количество слогов (приблизительно по пикам RMS)
            rms_normalized = rms / (np.max(rms) + 1e-6)
            peaks = librosa.util.peak_pick(rms_normalized, 3, 3, 3, 5, 0.3, 0.1)
            syllable_count = len(peaks)
            
            # Длительность аудио в секундах
            duration = len(audio) / sr
            
            # Темп речи (слоги в секунду)
            speech_rate = syllable_count / duration if duration > 0 else 0
            
            # Количество голосовых сегментов
            segment_count = np.sum(np.abs(np.diff(voiced_frames.astype(int)))) // 2
            
            return {
                'speech_rate': float(speech_rate),
                'syllable_count': syllable_count,
                'voiced_segments': segment_count,
                'speech_duration': duration
            }
            
        except Exception as e:
            logger.error(f"Error calculating speech rate: {str(e)}")
            return {
                'speech_rate': 0,
                'syllable_count': 0,
                'voiced_segments': 0,
                'speech_duration': 0
            }
    
    def _calculate_pause_features(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Расчет параметров пауз
        """
        try:
            # Определение пауз с помощью RMS
            frame_length = int(0.025 * sr)
            hop_length = int(0.010 * sr)
            rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Порог для определения пауз
            threshold = np.mean(rms) * 0.2
            
            # Определение неголосовых сегментов (пауз)
            pause_frames = rms < threshold
            
            # Преобразование в бинарную маску
            pause_mask = pause_frames.astype(int)
            
            # Поиск начала и конца пауз
            diffs = np.diff(np.concatenate(([0], pause_mask, [0])))
            pause_starts = np.where(diffs == 1)[0]
            pause_ends = np.where(diffs == -1)[0]
            
            # Длительности пауз в секундах
            pause_durations = (pause_ends - pause_starts) * hop_length / sr
            
            if len(pause_durations) == 0:
                return {
                    'pause_count': 0,
                    'pause_total_duration': 0,
                    'pause_mean_duration': 0,
                    'pause_std_duration': 0,
                    'pause_ratio': 0,
                    'pause_min_duration': 0,
                    'pause_max_duration': 0
                }
            
            # Статистика пауз
            pause_count = len(pause_durations)
            pause_total_duration = np.sum(pause_durations)
            pause_mean_duration = np.mean(pause_durations)
            pause_std_duration = np.std(pause_durations)
            pause_min_duration = np.min(pause_durations)
            pause_max_duration = np.max(pause_durations)
            
            # Доля пауз в записи
            total_duration = len(audio) / sr
            pause_ratio = pause_total_duration / total_duration if total_duration > 0 else 0
            
            return {
                'pause_count': float(pause_count),
                'pause_total_duration': float(pause_total_duration),
                'pause_mean_duration': float(pause_mean_duration),
                'pause_std_duration': float(pause_std_duration),
                'pause_ratio': float(pause_ratio),
                'pause_min_duration': float(pause_min_duration),
                'pause_max_duration': float(pause_max_duration)
            }
            
        except Exception as e:
            logger.error(f"Error calculating pause features: {str(e)}")
            return {
                'pause_count': 0,
                'pause_total_duration': 0,
                'pause_mean_duration': 0,
                'pause_std_duration': 0,
                'pause_ratio': 0,
                'pause_min_duration': 0,
                'pause_max_duration': 0
            }
    
    def _calculate_voice_activity_ratio(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """
        Расчет соотношения голосовой активности
        """
        try:
            # Используем голосовую активность из предыдущих расчетов
            frame_length = int(0.025 * sr)
            hop_length = int(0.010 * sr)
            rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Порог для определения речи
            threshold = np.mean(rms) * 0.3
            
            # Определение голосовых сегментов
            voiced_frames = rms > threshold
            voice_ratio = np.sum(voiced_frames) / len(voiced_frames) if len(voiced_frames) > 0 else 0
            
            # Общая длительность
            total_duration = len(audio) / sr
            
            # Длительность речи
            voice_duration = voice_ratio * total_duration
            
            return {
                'voice_activity_ratio': float(voice_ratio),
                'voice_duration': float(voice_duration),
                'silence_duration': float(total_duration - voice_duration),
                'total_duration': float(total_duration)
            }
            
        except Exception as e:
            logger.error(f"Error calculating voice activity ratio: {str(e)}")
            return {
                'voice_activity_ratio': 0,
                'voice_duration': 0,
                'silence_duration': 0,
                'total_duration': 0
            }
    
    async def analyze_results(self, ml_results: Dict[str, Any], audio: np.ndarray = None, sr: int = 16000) -> BurnoutResult:
        """
        Анализ результатов ML моделей и вынесение вердикта
        """
        try:
            # Извлекаем признаки из аудио
            acoustic_features = {}
            if audio is not None:
                # Расчет всех параметров
                pitch_features = self._calculate_pitch_features(audio, sr)
                intensity_features = self._calculate_intensity_features(audio, sr)
                speech_rate = self._calculate_speech_rate(audio, sr)
                pause_features = self._calculate_pause_features(audio, sr)
                voice_activity = self._calculate_voice_activity_ratio(audio, sr)
                
                acoustic_features = {
                    **pitch_features,
                    **intensity_features,
                    **speech_rate,
                    **pause_features,
                    **voice_activity
                }
            
            # Обработка результатов ML модели
            model_results = []
            total_score = 0
            total_confidence = 0
            
            for model_name, result in ml_results.items():
                all_probs = result.get('probabilities', {})
                rounded_probs = self._round_dict_values(all_probs)
                
                score = self._round_value(result.get('score', 0.5))
                confidence = self._round_value(result.get('confidence', 0.5))
                
                model_results.append(
                    ModelResult(
                        model_name=model_name,
                        score=score,
                        confidence=confidence,
                        prediction=result.get('predicted_emotion', 'unknown'),
                        all_probabilities=rounded_probs
                    )
                )
                total_score += score
                total_confidence += confidence
            
            # Средний балл
            avg_score = total_score / len(ml_results) if ml_results else 0
            avg_confidence = total_confidence / len(ml_results) if ml_results else 0
            
            avg_score = self._round_value(avg_score)
            avg_confidence = self._round_value(avg_confidence)
            
            # Преобразование в проценты
            final_score = avg_score * 100
            final_score = round(final_score, 1)
            
            # Определение уровня
            if final_score < 30:
                level = BurnoutLevel.LOW
                recommendations = [
                    "Continue monitoring your stress levels",
                    "Practice regular self-care",
                    "Maintain work-life balance"
                ]
            elif final_score < 50:
                level = BurnoutLevel.MODERATE
                recommendations = [
                    "Consider stress management techniques",
                    "Take regular breaks",
                    "Talk to your supervisor about workload"
                ]
            elif final_score < 70:
                level = BurnoutLevel.HIGH
                recommendations = [
                    "Seek professional support",
                    "Consider reducing work hours",
                    "Practice mindfulness and relaxation"
                ]
            else:
                level = BurnoutLevel.SEVERE
                recommendations = [
                    "URGENT: Seek professional help immediately",
                    "Take medical leave if possible",
                    "Contact employee assistance program"
                ]
            
            # Добавляем рекомендации на основе акустических признаков
            if audio is not None:
                if acoustic_features.get('pitch_variation', 1) < 0.3:
                    recommendations.append("Monotonous speech detected - consider vocal warm-up exercises")
                
                if acoustic_features.get('pause_ratio', 0) > 0.3:
                    recommendations.append("Frequent pauses detected - speech might be hesitant")
                
                if acoustic_features.get('speech_rate', 0) < 2:
                    recommendations.append("Slow speech rate - may indicate fatigue or depression")
                
                if acoustic_features.get('intensity_variation', 0) < 0.2:
                    recommendations.append("Low voice intensity variation - may indicate lack of energy")
            
            # Добавляем специфические рекомендации на основе эмоции
            if ml_results and 'wavlm_emotion' in ml_results:
                emotion = ml_results['wavlm_emotion'].get('predicted_emotion', '')
                if emotion == 'angry':
                    recommendations.append("Consider anger management techniques")
                elif emotion == 'sad':
                    recommendations.append("Consider activities that boost mood")
                elif emotion == 'fear':
                    recommendations.append("Consider anxiety reduction techniques")
                elif emotion == 'happy':
                    recommendations.append("Good emotional state, maintain healthy habits")
            
            # Собираем детальный анализ
            detailed_analysis = {
                "average_score": avg_score,
                "num_models": len(ml_results),
                "individual_scores": {
                    name: self._round_value(result.get('score', 0.5))
                    for name, result in ml_results.items()
                },
                "emotions": {
                    name: result.get('predicted_emotion', 'unknown')
                    for name, result in ml_results.items()
                }
            }
            
            # Добавляем вероятности модели
            for model_name, result in ml_results.items():
                if 'probabilities' in result:
                    detailed_analysis[f"{model_name}_probabilities"] = self._round_dict_values(
                        result['probabilities']
                    )
            
            # Добавляем акустические признаки
            if audio is not None:
                # Округляем акустические признаки
                acoustic_features_rounded = {
                    k: round(v, 3) if isinstance(v, float) and not np.isnan(v) else 0
                    for k, v in acoustic_features.items()
                }
                detailed_analysis["acoustic_features"] = acoustic_features_rounded
            
            return BurnoutResult(
                level=level,
                score=final_score,
                confidence=avg_confidence,
                recommendations=recommendations,
                model_results=model_results,
                detailed_analysis=detailed_analysis
            )
            
        except Exception as e:
            logger.error(f"Error analyzing results: {str(e)}")
            raise

    async def extract_combined_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Извлечение как классических аудио-признаков, так и подготовка аудио для модели
        """
        try:
            loop = asyncio.get_event_loop()
            features = await loop.run_in_executor(
                self.executor,
                self._extract_features_sync,
                audio
            )
            
            return {
                'feature_vector': features,
                'audio_signal': audio,
                'sample_rate': settings.SAMPLE_RATE
            }
            
        except Exception as e:
            logger.error(f"Error extracting combined features: {str(e)}")
            raise

    async def analyze_with_burnout_algorithm(
        self,
        current_result: Dict[str, Any],
        baseline_result: Dict[str, Any],
        history: List[Dict[str, Any]] = None,
        windows: List[Dict[str, Any]] = None,  # Пока не используется
        audio_quality: float = 0.8,
        baseline_reliability: float = 0.7
    ) -> Dict[str, Any]:
        """
        Анализ с использованием полного алгоритма выгорания
        """
        from app.core.services.burnout_analyzer import BurnoutAnalyzer, State
        
        analyzer = BurnoutAnalyzer()
        
        if history is None:
            history = []
        
        # Не передаем windows, так как в текущей версии он не используется
        result = analyzer.analyze(
            current=current_result,
            baseline=baseline_result,
            history=history,
            audio_quality=audio_quality,
            baseline_reliability=baseline_reliability
        )
        
        return result
        