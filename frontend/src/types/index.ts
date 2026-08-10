export interface EmotionProbabilities {
  neutral: number;
  happy: number;
  sad: number;
  angry: number;
  fear: number;
  disgust: number;
  surprise: number;
}

export interface AcousticFeatures {
  pitch_mean: number;
  pitch_std: number;
  pitch_range: number;
  pitch_min: number;
  pitch_max: number;
  pitch_variation: number;
  intensity_mean: number;
  intensity_std: number;
  intensity_min: number;
  intensity_max: number;
  intensity_variation: number;
  dynamic_range: number;
  speech_rate: number;
  syllable_count: number;
  voiced_segments: number;
  speech_duration: number;
  pause_count: number;
  pause_total_duration: number;
  pause_mean_duration: number;
  pause_std_duration: number;
  pause_ratio: number;
  pause_min_duration: number;
  pause_max_duration: number;
  voice_activity_ratio: number;
  voice_duration: number;
  silence_duration: number;
  total_duration: number;
}

export interface ModelResult {
  model_name: string;
  score: number;
  confidence: number;
  prediction: string;
  all_probabilities: EmotionProbabilities;
}

export interface BurnoutResult {
  level: 'low' | 'moderate' | 'high' | 'severe';
  score: number;
  confidence: number;
  recommendations: string[];
  model_results: ModelResult[];
  detailed_analysis: {
    average_score: number;
    num_models: number;
    individual_scores: Record<string, number>;
    emotions: Record<string, string>;
    acoustic_features?: AcousticFeatures;
    [key: string]: any;
  };
}

export interface AnalysisResponse {
  status: 'pending' | 'processing' | 'success' | 'failed';
  result?: BurnoutResult;
  metadata: {
    filename: string;
    duration_seconds: number;
    sample_rate: number;
    user_id?: string;
    session_id?: string;
    processed_at: string;
  };
  error?: string;
  processing_time_ms?: number;
}

export interface BurnoutAnalysisResult {
  state: 'NORMAL' | 'SHORT_STRESS' | 'SUSTAINED_STRESS' | 'BURNOUT_LIKE' | 'LOW_AFFECT_UNSPECIFIC' | 'INSUFFICIENT_DATA';
  risk: number;
  score: number;
  level: string;
  confidence: number;
  top_factor: string;
  components: {
    emotional_exhaustion: number;
    prosodic_flattening: number;
    pause_tempo: number;
    negative_activation: number;
    positive_affect_loss: number;
  };
  recommendations: string[];
  comment?: string;
}

export interface BaselineData {
  acoustic_features: Partial<AcousticFeatures>;
  detailed_analysis: {
    wavlm_emotion_probabilities: EmotionProbabilities;
  };
  model_results: ModelResult[];
}

export interface HistoryRecord {
  risk: number;
  state: string;
  timestamp?: string;
}