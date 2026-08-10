import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging
from collections import deque

from app.models.response_models import BurnoutLevel, BurnoutResult, ModelResult

logger = logging.getLogger(__name__)

class State(str, Enum):
    NORMAL = "NORMAL"
    SHORT_STRESS = "SHORT_STRESS"
    SUSTAINED_STRESS = "SUSTAINED_STRESS"
    BURNOUT_LIKE = "BURNOUT_LIKE"
    LOW_AFFECT_UNSPECIFIC = "LOW_AFFECT_UNSPECIFIC"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class BurnoutAnalyzer:
    """
    Анализатор для вычисления уровня выгорания на основе текущего и baseline результатов
    Строго по схеме:
    - Emotional Exhaustion (25%): sad (70%) + neutral (30%)
    - Prosodic Flattening (25%): pitch_variation (50%) + pitch_range (30%) + intensity_variation (20%)
    - Pause/Tempo (20%): pause_ratio (40%) + pause_mean (20%) + pause_max (10%) + speech_rate (30%)
    - Negative Activation (15%): angry (40%) + fear (35%) + disgust (25%)
    - Positive Affect Loss (15%): happy (100%)
    """
    
    def __init__(self):
        # Веса для компонентов (согласно схеме)
        self.weights = {
            'exhaustion': 0.25,
            'prosodic_flattening': 0.25,
            'pause_tempo': 0.20,
            'negative_activation': 0.15,
            'positive_affect_loss': 0.15
        }
        
        # Внутренние веса компонентов
        self.component_weights = {
            'exhaustion': {'sad': 0.70, 'neutral': 0.30},
            'prosodic_flattening': {'pitch_variation': 0.50, 'pitch_range': 0.30, 'intensity_variation': 0.20},
            'pause_tempo': {'pause_ratio': 0.40, 'pause_mean': 0.20, 'pause_max': 0.10, 'speech_rate': 0.30},
            'negative_activation': {'angry': 0.40, 'fear': 0.35, 'disgust': 0.25},
            'positive_affect_loss': {'happy': 1.00}
        }
        
        # Пороги для состояний (согласно схеме)
        self.thresholds = {
            'risk': {
                'normal': 0.35,
                'mild': 0.49,
                'moderate': 0.64,
                'severe': 0.65
            }
        }
        
        self.history = deque(maxlen=6)
        
    def _normalize_emotion_delta(self, current: float, baseline: float) -> float:
        """
        Нормализация изменения эмоции по схеме:
        рост <0.05 → 0; 0.05–0.20 → линейно; ≥0.20 → 1
        """
        delta = current - baseline
        if delta < 0.05:
            return 0.0
        elif delta >= 0.20:
            return 1.0
        else:
            return (delta - 0.05) / 0.15
    
    def _normalize_emotion_drop(self, baseline: float, current: float) -> float:
        """
        Нормализация падения эмоции (для happy):
        падение <0.05 → 0; 0.05–0.20 → линейно; ≥0.20 → 1
        """
        delta = baseline - current
        if delta < 0.05:
            return 0.0
        elif delta >= 0.20:
            return 1.0
        else:
            return (delta - 0.05) / 0.15
    
    def _normalize_acoustic_drop(self, baseline: float, current: float, deadzone: float = 0.10, threshold: float = 0.35) -> float:
        """
        Нормализация падения акустического показателя по схеме:
        падение <10% → 0; 10–35% → линейно; ≥35% → 1
        """
        if baseline <= 0:
            return 0.0
        
        relative_drop = (baseline - current) / baseline
        
        if relative_drop < deadzone:
            return 0.0
        elif relative_drop >= threshold:
            return 1.0
        else:
            return (relative_drop - deadzone) / (threshold - deadzone)
    
    def _normalize_acoustic_increase(self, baseline: float, current: float, deadzone: float = 0.15, threshold: float = 0.50) -> float:
        """
        Нормализация увеличения акустического показателя по схеме:
        рост <15% → 0; 15–50% → линейно; ≥50% → 1
        """
        if baseline <= 0:
            return 0.0 if current < 0.05 else 1.0
        
        relative_increase = (current - baseline) / baseline
        
        if relative_increase < deadzone:
            return 0.0
        elif relative_increase >= threshold:
            return 1.0
        else:
            return (relative_increase - deadzone) / (threshold - deadzone)
    
    def _normalize_speech_rate_drop(self, baseline: float, current: float) -> float:
        """
        Нормализация падения speech_rate по схеме:
        падение <10% → 0; 10–30% → линейно; ≥30% → 1
        """
        if baseline <= 0 or current == 0:
            return 0.0
        
        relative_drop = (baseline - current) / baseline
        
        if relative_drop < 0.10:
            return 0.0
        elif relative_drop >= 0.30:
            return 1.0
        else:
            return (relative_drop - 0.10) / 0.20
    
    def _get_acoustic_feature(self, data: Dict, key: str, default: float = 0.0) -> float:
        """Безопасное получение акустического признака"""
        if 'acoustic_features' in data and key in data['acoustic_features']:
            return float(data['acoustic_features'][key])
        return default
    
    def _get_emotion_probabilities(self, data: Dict) -> Dict[str, float]:
        """Извлечение вероятностей эмоций из результата"""
        probs = {}
        
        if 'model_results' in data and data['model_results']:
            for model_result in data['model_results']:
                if 'all_probabilities' in model_result:
                    return model_result['all_probabilities']
        
        if 'detailed_analysis' in data:
            for key, value in data['detailed_analysis'].items():
                if 'probabilities' in key and isinstance(value, dict):
                    return value
        
        return {'sad': 0, 'neutral': 0, 'happy': 0, 'angry': 0, 'fear': 0, 'disgust': 0, 'surprise': 0}
    
    # ==================== КОМПОНЕНТ 1: EMOTIONAL EXHAUSTION (25%) ====================
    
    def calculate_emotional_exhaustion(self, current: Dict, baseline: Dict) -> float:
        """
        Emotional Exhaustion:
        - sad_increase_score: 70%
        - neutral_increase_score: 30%
        """
        current_probs = self._get_emotion_probabilities(current)
        baseline_probs = self._get_emotion_probabilities(baseline)
        
        # Расчет sad_increase_score
        sad_score = self._normalize_emotion_delta(
            current_probs.get('sad', 0),
            baseline_probs.get('sad', 0)
        )
        
        # Расчет neutral_increase_score
        neutral_score = self._normalize_emotion_delta(
            current_probs.get('neutral', 0),
            baseline_probs.get('neutral', 0)
        )
        
        # Итоговый скор
        exhaustion = 0.70 * sad_score + 0.30 * neutral_score
        
        logger.debug(f"Exhaustion: sad={sad_score:.3f}, neutral={neutral_score:.3f}, result={exhaustion:.3f}")
        return exhaustion
    
    # ==================== КОМПОНЕНТ 2: PROSODIC FLATTENING (25%) ====================
    
    def calculate_prosodic_flattening(self, current: Dict, baseline: Dict) -> float:
        """
        Prosodic Flattening:
        - pitch_variation_decrease_score: 50%
        - pitch_range_decrease_score: 30%
        - intensity_variation_decrease_score: 20%
        """
        current_pitch_var = self._get_acoustic_feature(current, 'pitch_variation', 0.1)
        baseline_pitch_var = self._get_acoustic_feature(baseline, 'pitch_variation', 0.1)
        
        current_pitch_range = self._get_acoustic_feature(current, 'pitch_range', 50)
        baseline_pitch_range = self._get_acoustic_feature(baseline, 'pitch_range', 50)
        
        current_intensity_var = self._get_acoustic_feature(current, 'intensity_variation', 0.1)
        baseline_intensity_var = self._get_acoustic_feature(baseline, 'intensity_variation', 0.1)
        
        # Расчет с deadzone 10% и порогом 35%
        pitch_var_drop = self._normalize_acoustic_drop(baseline_pitch_var, current_pitch_var)
        pitch_range_drop = self._normalize_acoustic_drop(baseline_pitch_range, current_pitch_range)
        intensity_var_drop = self._normalize_acoustic_drop(baseline_intensity_var, current_intensity_var)
        
        # Итоговый скор
        flattening = (
            0.50 * pitch_var_drop +
            0.30 * pitch_range_drop +
            0.20 * intensity_var_drop
        )
        
        logger.debug(f"ProsodicFlattening: pitch_var={pitch_var_drop:.3f}, pitch_range={pitch_range_drop:.3f}, intensity={intensity_var_drop:.3f}, result={flattening:.3f}")
        return flattening
    
    # ==================== КОМПОНЕНТ 3: PAUSE / TEMPO (20%) ====================
    
    def calculate_pause_tempo(self, current: Dict, baseline: Dict) -> float:
        """
        Pause/Tempo:
        - pause_ratio_increase_score: 40%
        - pause_mean_increase_score: 20%
        - pause_max_increase_score: 10%
        - speech_rate_decrease_score: 30%
        
        Если speech_rate=0, исключается, веса нормализуются
        """
        current_pause_ratio = self._get_acoustic_feature(current, 'pause_ratio', 0.1)
        baseline_pause_ratio = self._get_acoustic_feature(baseline, 'pause_ratio', 0.1)
        
        current_pause_mean = self._get_acoustic_feature(current, 'pause_mean_duration', 0.05)
        baseline_pause_mean = self._get_acoustic_feature(baseline, 'pause_mean_duration', 0.05)
        
        current_pause_max = self._get_acoustic_feature(current, 'pause_max_duration', 0.1)
        baseline_pause_max = self._get_acoustic_feature(baseline, 'pause_max_duration', 0.1)
        
        current_speech_rate = self._get_acoustic_feature(current, 'speech_rate', 0)
        baseline_speech_rate = self._get_acoustic_feature(baseline, 'speech_rate', 3.0)
        
        # Расчет с deadzone 15% и порогом 50%
        pause_ratio_up = self._normalize_acoustic_increase(baseline_pause_ratio, current_pause_ratio)
        pause_mean_up = self._normalize_acoustic_increase(baseline_pause_mean, current_pause_mean)
        pause_max_up = self._normalize_acoustic_increase(baseline_pause_max, current_pause_max)
        
        # Проверяем, есть ли speech_rate
        has_speech_rate = current_speech_rate > 0 and baseline_speech_rate > 0
        
        if has_speech_rate:
            speech_rate_drop = self._normalize_speech_rate_drop(baseline_speech_rate, current_speech_rate)
            pause_tempo = (
                0.40 * pause_ratio_up +
                0.20 * pause_mean_up +
                0.10 * pause_max_up +
                0.30 * speech_rate_drop
            )
        else:
            # Без speech_rate: нормализуем веса для первых трех компонентов
            # Сумма весов = 0.40 + 0.20 + 0.10 = 0.70
            pause_tempo = (
                (0.40 / 0.70) * pause_ratio_up +
                (0.20 / 0.70) * pause_mean_up +
                (0.10 / 0.70) * pause_max_up
            )
        
        logger.debug(f"PauseTempo: ratio={pause_ratio_up:.3f}, mean={pause_mean_up:.3f}, max={pause_max_up:.3f}, rate={speech_rate_drop if has_speech_rate else 0:.3f}, result={pause_tempo:.3f}")
        return pause_tempo
    
    # ==================== КОМПОНЕНТ 4: NEGATIVE ACTIVATION (15%) ====================
    
    def calculate_negative_activation(self, current: Dict, baseline: Dict) -> float:
        """
        Negative Activation:
        - angry_increase_score: 40%
        - fear_increase_score: 35%
        - disgust_increase_score: 25%
        """
        current_probs = self._get_emotion_probabilities(current)
        baseline_probs = self._get_emotion_probabilities(baseline)
        
        angry_score = self._normalize_emotion_delta(
            current_probs.get('angry', 0),
            baseline_probs.get('angry', 0)
        )
        fear_score = self._normalize_emotion_delta(
            current_probs.get('fear', 0),
            baseline_probs.get('fear', 0)
        )
        disgust_score = self._normalize_emotion_delta(
            current_probs.get('disgust', 0),
            baseline_probs.get('disgust', 0)
        )
        
        negative_activation = (
            0.40 * angry_score +
            0.35 * fear_score +
            0.25 * disgust_score
        )
        
        logger.debug(f"NegativeActivation: angry={angry_score:.3f}, fear={fear_score:.3f}, disgust={disgust_score:.3f}, result={negative_activation:.3f}")
        return negative_activation
    
    # ==================== КОМПОНЕНТ 5: POSITIVE AFFECT LOSS (15%) ====================
    
    def calculate_positive_affect_loss(self, current: Dict, baseline: Dict) -> float:
        """
        Positive Affect Loss:
        - happy_drop_score: 100%
        """
        current_probs = self._get_emotion_probabilities(current)
        baseline_probs = self._get_emotion_probabilities(baseline)
        
        happy_score = self._normalize_emotion_drop(
            baseline_probs.get('happy', 0),
            current_probs.get('happy', 0)
        )
        
        logger.debug(f"PositiveAffectLoss: happy_drop={happy_score:.3f}")
        return happy_score
    
    # ==================== ИТОГОВЫЙ РАСЧЕТ ====================
    
    def calculate_raw_risk(self, components: Dict[str, float]) -> float:
        """
        Burnout Risk:
        25% Exhaustion + 25% Prosodic Flattening + 20% Pause/Tempo + 15% Negative Activation + 15% Positive Affect Loss
        """
        raw_risk = (
            self.weights['exhaustion'] * components['exhaustion'] +
            self.weights['prosodic_flattening'] * components['prosodic_flattening'] +
            self.weights['pause_tempo'] * components['pause_tempo'] +
            self.weights['negative_activation'] * components['negative_activation'] +
            self.weights['positive_affect_loss'] * components['positive_affect_loss']
        )
        
        return min(1.0, max(0.0, raw_risk))
    
    def determine_level(self, risk: float) -> tuple:
        """
        Определение уровня по схеме:
        <35% normal; 35–49% mild; 50–64% moderate; ≥65% severe
        """
        if risk < 0.35:
            return BurnoutLevel.LOW, "normal"
        elif risk < 0.50:
            return BurnoutLevel.MODERATE, "mild"
        elif risk < 0.65:
            return BurnoutLevel.HIGH, "moderate"
        else:
            return BurnoutLevel.SEVERE, "severe"
    
    def get_top_factor(self, components: Dict[str, float]) -> str:
        """Определение доминирующего фактора"""
        max_component = max(components.items(), key=lambda x: x[1])
        factor_names = {
            'exhaustion': 'Emotional Exhaustion',
            'prosodic_flattening': 'Prosodic Flattening',
            'pause_tempo': 'Pause/Tempo Changes',
            'negative_activation': 'Negative Activation',
            'positive_affect_loss': 'Positive Affect Loss'
        }
        return factor_names.get(max_component[0], 'Unknown')
    
    def generate_recommendations(self, level: BurnoutLevel, top_factor: str, components: Dict[str, float]) -> List[str]:
        """Генерация рекомендаций на основе уровня и факторов"""
        recommendations = []
        
        if level == BurnoutLevel.SEVERE:
            recommendations = [
                "🚨 URGENT: Seek professional psychological help immediately",
                "Take medical leave if possible",
                "Contact employee assistance program",
                "Reduce work hours and delegate tasks",
                "Practice self-care and stress management techniques"
            ]
        elif level == BurnoutLevel.HIGH:
            recommendations = [
                "⚠️ Moderate risk detected - take action to prevent burnout",
                "Schedule regular breaks throughout the day",
                "Consider therapy or counseling sessions",
                "Implement relaxation techniques",
                "Discuss workload with your supervisor"
            ]
        elif level == BurnoutLevel.MODERATE:
            recommendations = [
                "⚡ Mild risk detected - monitor your state",
                "Take regular breaks and practice mindfulness",
                "Ensure adequate sleep and nutrition",
                "Exercise and physical activity recommended"
            ]
        else:  # LOW
            recommendations = [
                "✅ Normal emotional state detected",
                "Continue maintaining healthy habits",
                "Practice preventive self-care",
                "Regular check-ups recommended"
            ]
        
        # Добавляем специфические рекомендации на основе доминирующего фактора
        if components.get('exhaustion', 0) > 0.5:
            recommendations.append("Emotional exhaustion detected - prioritize mental health")
        if components.get('prosodic_flattening', 0) > 0.5:
            recommendations.append("Voice monotony detected - speech therapy may help")
        if components.get('pause_tempo', 0) > 0.5:
            recommendations.append("Speech pattern changes - consider vocal rest")
        if components.get('negative_activation', 0) > 0.5:
            recommendations.append("High negative activation - consider anger/stress management")
        if components.get('positive_affect_loss', 0) > 0.5:
            recommendations.append("Reduced positive affect - consider activities that boost mood")
        
        return recommendations
    
    def analyze(self, 
                current: Dict[str, Any], 
                baseline: Dict[str, Any],
                history: List[Dict[str, Any]] = None,
                audio_quality: float = 0.8,
                baseline_reliability: float = 0.7) -> Dict[str, Any]:
        """
        Основной метод анализа по схеме
        """
        try:
            logger.info("Starting burnout analysis...")
            
            # Проверка наличия baseline
            if not baseline:
                return {
                    'state': State.INSUFFICIENT_DATA.value,
                    'risk': 0.0,
                    'score': 0,
                    'level': 'normal',
                    'confidence': 0.0,
                    'components': {},
                    'top_factor': 'No baseline provided',
                    'recommendations': ["⚠️ Baseline required for analysis"],
                    'error': 'Baseline not provided'
                }
            
            # 1. Расчет компонентов
            components = {
                'exhaustion': self.calculate_emotional_exhaustion(current, baseline),
                'prosodic_flattening': self.calculate_prosodic_flattening(current, baseline),
                'pause_tempo': self.calculate_pause_tempo(current, baseline),
                'negative_activation': self.calculate_negative_activation(current, baseline),
                'positive_affect_loss': self.calculate_positive_affect_loss(current, baseline)
            }
            
            # 2. Расчет сырого риска
            raw_risk = self.calculate_raw_risk(components)
            
            # 3. Расчет уровня
            level, level_name = self.determine_level(raw_risk)
            
            # 4. Определение доминирующего фактора
            top_factor = self.get_top_factor(components)
            
            # 5. Расчет уверенности
            confidence = (
                0.30 * audio_quality +
                0.25 * baseline_reliability +
                0.25 * 0.5  # persistence (без истории используем базовое значение)
            )
            confidence = min(1.0, confidence)
            
            # 6. Генерация рекомендаций
            recommendations = self.generate_recommendations(level, top_factor, components)
            
            # 7. Формирование результата
            result = {
                'state': level_name.upper(),
                'risk': round(raw_risk, 3),
                'score': round(raw_risk * 100, 1),
                'level': level_name,
                'confidence': round(confidence, 3),
                'top_factor': top_factor,
                'components': {
                    'emotional_exhaustion': round(components['exhaustion'], 3),
                    'prosodic_flattening': round(components['prosodic_flattening'], 3),
                    'pause_tempo': round(components['pause_tempo'], 3),
                    'negative_activation': round(components['negative_activation'], 3),
                    'positive_affect_loss': round(components['positive_affect_loss'], 3)
                },
                'recommendations': recommendations,
                'comment': "Без истории нескольких текущих записей нельзя надежно различить short stress vs chronic burnout"
            }
            
            logger.info(f"Analysis complete: State={level_name}, Score={result['score']}, Confidence={result['confidence']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in burnout analysis: {str(e)}", exc_info=True)
            return {
                'state': State.INSUFFICIENT_DATA.value,
                'risk': 0.0,
                'score': 0,
                'level': 'unknown',
                'confidence': 0.0,
                'components': {},
                'top_factor': 'Error',
                'recommendations': ["⚠️ Error in analysis. Please try again."],
                'error': str(e)
            }