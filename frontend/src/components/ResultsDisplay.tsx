import React from 'react';
import { 
  Activity, 
  Brain, 
  Mic, 
  Clock, 
  AlertCircle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react';
import { AnalysisResponse, BurnoutAnalysisResult, BurnoutResult } from '../types';

interface ResultsDisplayProps {
  result: AnalysisResponse | BurnoutAnalysisResult;
  isBurnoutAnalysis?: boolean;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ result, isBurnoutAnalysis = false }) => {
  if (!result) return null;

  // Для анализа с baseline
  if (isBurnoutAnalysis && 'state' in result) {
    const analysis = result as BurnoutAnalysisResult;
    const stateColors: Record<string, string> = {
      NORMAL: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
      SHORT_STRESS: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
      SUSTAINED_STRESS: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
      BURNOUT_LIKE: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
      LOW_AFFECT_UNSPECIFIC: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
      INSUFFICIENT_DATA: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
    };

    const stateIcons: Record<string, React.ReactNode> = {
      NORMAL: <CheckCircle className="w-5 h-5" />,
      SHORT_STRESS: <AlertCircle className="w-5 h-5" />,
      SUSTAINED_STRESS: <Activity className="w-5 h-5" />,
      BURNOUT_LIKE: <AlertCircle className="w-5 h-5" />,
      LOW_AFFECT_UNSPECIFIC: <Minus className="w-5 h-5" />,
      INSUFFICIENT_DATA: <AlertCircle className="w-5 h-5" />,
    };

    const stateDescriptions: Record<string, string> = {
      NORMAL: 'Normal emotional state. Continue maintaining healthy habits.',
      SHORT_STRESS: 'Short-term stress detected. Rest and recover.',
      SUSTAINED_STRESS: 'Sustained stress detected. Take action to prevent burnout.',
      BURNOUT_LIKE: 'Burnout-like pattern detected. Seek professional help.',
      LOW_AFFECT_UNSPECIFIC: 'Low affect state. Monitor your emotional state.',
      INSUFFICIENT_DATA: 'Insufficient data for reliable analysis.',
    };

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Analysis Results</h2>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Confidence: {(analysis.confidence * 100).toFixed(0)}%
          </span>
        </div>

        {/* State Badge */}
        <div className={`flex items-center gap-3 p-4 rounded-xl ${stateColors[analysis.state]}`}>
          {stateIcons[analysis.state]}
          <div>
            <div className="font-semibold">{analysis.state}</div>
            <div className="text-sm opacity-80">{stateDescriptions[analysis.state]}</div>
          </div>
          <div className="ml-auto text-right">
            <div className="text-2xl font-bold">{analysis.score}%</div>
            <div className="text-sm opacity-80">Risk Score</div>
          </div>
        </div>

        {/* Components */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(analysis.components).map(([key, value]) => {
            const labels: Record<string, string> = {
              emotional_exhaustion: 'Emotional Exhaustion',
              prosodic_flattening: 'Prosodic Flattening',
              pause_tempo: 'Pause/Tempo',
              negative_activation: 'Negative Activation',
              positive_affect_loss: 'Positive Affect Loss',
            };
            return (
              <div key={key} className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                    {labels[key] || key}
                  </span>
                  <span className="text-sm font-semibold">{(value * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full transition-all duration-500"
                    style={{ width: `${value * 100}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Top Factor */}
        <div className="bg-primary-50 dark:bg-primary-900/20 rounded-xl p-4">
          <span className="text-sm text-gray-600 dark:text-gray-300">Top Factor: </span>
          <span className="font-semibold text-primary-700 dark:text-primary-300">
            {analysis.top_factor}
          </span>
        </div>

        {/* Recommendations */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Recommendations
          </h3>
          <ul className="space-y-2">
            {analysis.recommendations.map((rec, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                <span className="text-primary-500 mt-0.5">•</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>

        {analysis.comment && (
          <div className="text-sm text-gray-500 dark:text-gray-400 italic">
            {analysis.comment}
          </div>
        )}
      </div>
    );
  }

  // Для обычного анализа
  const analysis = result as AnalysisResponse;
  if (!analysis.result) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-8">
        No results available
      </div>
    );
  }

  const burnoutResult = analysis.result;
  const levelColors: Record<string, string> = {
    low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    moderate: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
    severe: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Analysis Results</h2>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {analysis.processing_time_ms && `${analysis.processing_time_ms.toFixed(0)}ms`}
        </span>
      </div>

      {/* Level */}
      <div className={`flex items-center gap-3 p-4 rounded-xl ${levelColors[burnoutResult.level]}`}>
        <Activity className="w-5 h-5" />
        <div>
          <div className="font-semibold capitalize">{burnoutResult.level}</div>
          <div className="text-sm opacity-80">Burnout Level</div>
        </div>
        <div className="ml-auto text-right">
          <div className="text-2xl font-bold">{burnoutResult.score.toFixed(0)}%</div>
          <div className="text-sm opacity-80">Score</div>
        </div>
      </div>

      {/* Emotions */}
      {burnoutResult.model_results[0]?.all_probabilities && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Emotion Probabilities
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(burnoutResult.model_results[0].all_probabilities).map(([emotion, value]) => (
              <div key={emotion} className="flex justify-between items-center p-2 bg-white dark:bg-gray-700 rounded-lg">
                <span className="text-sm capitalize text-gray-600 dark:text-gray-300">{emotion}</span>
                <span className="text-sm font-medium">{(value * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Acoustic Features */}
      {burnoutResult.detailed_analysis?.acoustic_features && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            <Mic className="w-4 h-4 inline mr-1" />
            Acoustic Features
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {Object.entries(burnoutResult.detailed_analysis.acoustic_features)
              .filter(([_, value]) => typeof value === 'number')
              .slice(0, 9)
              .map(([key, value]) => (
                <div key={key} className="flex justify-between items-center p-2 bg-white dark:bg-gray-700 rounded-lg">
                  <span className="text-xs text-gray-600 dark:text-gray-300">{key.replace(/_/g, ' ')}</span>
                  <span className="text-xs font-medium">{(value as number).toFixed(2)}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Recommendations
        </h3>
        <ul className="space-y-2">
          {burnoutResult.recommendations.map((rec, index) => (
            <li key={index} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
              <span className="text-primary-500 mt-0.5">•</span>
              {rec}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default ResultsDisplay;