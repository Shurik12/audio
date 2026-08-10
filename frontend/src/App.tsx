import React, { useState, useCallback } from 'react';

// Типы для ответа анализа с baseline
interface AnalysisResult {
  status: string;
  analysis: {
    state: string;
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
  };
  current_result: any;
  baseline_used: any;
  metadata: {
    filename: string;
    duration_seconds: number;
    user_id?: string;
    processed_at: string;
  };
  processing_time_ms: number;
}

// Дефолтный baseline (будет использоваться если не передан)
const DEFAULT_BASELINE = {
  acoustic_features: {
    pitch_variation: 0.19,
    pitch_range: 60.0,
    intensity_variation: 0.3,
    pause_ratio: 0.15,
    pause_mean_duration: 0.05,
    pause_max_duration: 0.10,
    speech_rate: 3.5
  },
  detailed_analysis: {
    wavlm_emotion_probabilities: {
      neutral: 0.2,
      happy: 0.3,
      sad: 0.1,
      angry: 0.05,
      fear: 0.05,
      disgust: 0.03,
      surprise: 0.05
    }
  }
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [useCustomBaseline, setUseCustomBaseline] = useState(false);

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      // Если используем кастомный baseline - передаем его
      if (useCustomBaseline) {
        formData.append('baseline_data', JSON.stringify(DEFAULT_BASELINE));
      }
      
      // Добавляем user_id (опционально)
      formData.append('user_id', 'user_123');

      const response = await fetch('/api/audio/analyze-with-baseline', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const data = await response.json();
      setResult(data);
      console.log('Analysis result:', data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [useCustomBaseline]);

  const getLevelColor = (level: string) => {
    const colors: Record<string, string> = {
      low: '#22c55e',
      mild: '#eab308',
      moderate: '#f97316',
      severe: '#ef4444',
      normal: '#22c55e'
    };
    return colors[level] || '#6b7280';
  };

  const getStateEmoji = (state: string) => {
    const emojis: Record<string, string> = {
      NORMAL: '✅',
      SHORT_STRESS: '⚡',
      SUSTAINED_STRESS: '⚠️',
      BURNOUT_LIKE: '🚨',
      LOW_AFFECT_UNSPECIFIC: '📉',
      INSUFFICIENT_DATA: '❓'
    };
    return emojis[state] || '📊';
  };

  return (
    <div style={{ 
      padding: '20px', 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      maxWidth: '1000px',
      margin: '0 auto',
      minHeight: '100vh',
      background: '#f8fafc'
    }}>
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '32px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
      }}>
        <h1 style={{ 
          color: '#2563eb', 
          fontSize: '28px',
          marginBottom: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <span>🧠</span> Burnout Detector
        </h1>
        <p style={{ color: '#6b7280', marginBottom: '20px' }}>
          AI-powered analysis with personal baseline comparison
        </p>
        
        {/* Baseline Toggle */}
        <div style={{ 
          marginBottom: '20px',
          padding: '16px',
          background: '#f1f5f9',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={useCustomBaseline}
              onChange={(e) => setUseCustomBaseline(e.target.checked)}
              style={{ width: '18px', height: '18px' }}
            />
            <span style={{ fontSize: '14px', fontWeight: '500' }}>
              Use custom baseline (default values)
            </span>
          </label>
          <span style={{ fontSize: '12px', color: '#6b7280' }}>
            {useCustomBaseline ? '✅ Baseline will be sent' : 'ℹ️ Server will use default baseline'}
          </span>
        </div>
        
        {/* Upload Area */}
        <div style={{ 
          padding: '30px',
          border: '2px dashed #d1d5db',
          borderRadius: '12px',
          textAlign: 'center',
          background: '#f9fafb'
        }}>
          <input
            type="file"
            accept="audio/*"
            onChange={handleFileUpload}
            disabled={isLoading}
            style={{ 
              padding: '12px',
              fontSize: '16px',
              cursor: 'pointer',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              background: 'white',
              width: '100%',
              maxWidth: '400px'
            }}
          />
          {file && (
            <p style={{ marginTop: '12px', color: '#16a34a' }}>
              ✅ {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
            </p>
          )}
          <p style={{ marginTop: '12px', fontSize: '12px', color: '#9ca3af' }}>
            Supported formats: WAV, MP3, M4A, FLAC • Max 50MB • Max 5 minutes
          </p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div style={{ 
            textAlign: 'center', 
            padding: '40px 20px',
            marginTop: '20px'
          }}>
            <div style={{
              display: 'inline-block',
              width: '40px',
              height: '40px',
              border: '4px solid #e5e7eb',
              borderTop: '4px solid #2563eb',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }} />
            <p style={{ marginTop: '12px', color: '#4b5563' }}>
              Analyzing audio with baseline comparison...
            </p>
            <style>{`
              @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
              }
            `}</style>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div style={{
            marginTop: '20px',
            padding: '16px',
            background: '#fee2e2',
            borderRadius: '8px',
            color: '#dc2626'
          }}>
            <strong>❌ Error:</strong> {error}
          </div>
        )}

        {/* Results */}
        {result && result.analysis && (
          <div style={{ marginTop: '24px' }}>
            <h2 style={{ 
              fontSize: '20px',
              marginBottom: '16px',
              borderBottom: '2px solid #e5e7eb',
              paddingBottom: '12px'
            }}>
              📊 Analysis Results
            </h2>
            
            {/* State & Score Cards */}
            <div style={{ 
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '16px',
              marginBottom: '20px'
            }}>
              <div style={{ 
                padding: '16px', 
                background: '#f9fafb', 
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ color: '#6b7280', fontSize: '12px', textTransform: 'uppercase' }}>
                  State
                </div>
                <div style={{ 
                  fontSize: '24px', 
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}>
                  <span>{getStateEmoji(result.analysis.state)}</span>
                  <span style={{ 
                    color: getLevelColor(result.analysis.level),
                    fontSize: '18px'
                  }}>
                    {result.analysis.state}
                  </span>
                </div>
              </div>
              <div style={{ 
                padding: '16px', 
                background: '#f9fafb', 
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ color: '#6b7280', fontSize: '12px', textTransform: 'uppercase' }}>
                  Risk Score
                </div>
                <div style={{ fontSize: '28px', fontWeight: 'bold' }}>
                  {result.analysis.score}%
                </div>
              </div>
              <div style={{ 
                padding: '16px', 
                background: '#f9fafb', 
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ color: '#6b7280', fontSize: '12px', textTransform: 'uppercase' }}>
                  Confidence
                </div>
                <div style={{ fontSize: '28px', fontWeight: 'bold' }}>
                  {(result.analysis.confidence * 100).toFixed(0)}%
                </div>
              </div>
              <div style={{ 
                padding: '16px', 
                background: '#f9fafb', 
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ color: '#6b7280', fontSize: '12px', textTransform: 'uppercase' }}>
                  Top Factor
                </div>
                <div style={{ fontSize: '16px', fontWeight: 'bold' }}>
                  {result.analysis.top_factor}
                </div>
              </div>
            </div>

            {/* Components */}
            <div style={{ 
              padding: '16px', 
              background: '#f9fafb', 
              borderRadius: '8px',
              marginBottom: '16px'
            }}>
              <h3 style={{ marginTop: 0, fontSize: '16px', marginBottom: '12px' }}>
                📈 Component Scores
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                {Object.entries(result.analysis.components).map(([key, value]) => {
                  const labels: Record<string, string> = {
                    emotional_exhaustion: 'Emotional Exhaustion',
                    prosodic_flattening: 'Prosodic Flattening',
                    pause_tempo: 'Pause/Tempo',
                    negative_activation: 'Negative Activation',
                    positive_affect_loss: 'Positive Affect Loss'
                  };
                  return (
                    <div key={key}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                        <span style={{ color: '#4b5563' }}>{labels[key] || key}</span>
                        <span style={{ fontWeight: 'bold' }}>{(value * 100).toFixed(0)}%</span>
                      </div>
                      <div style={{ 
                        width: '100%', 
                        height: '6px', 
                        background: '#e5e7eb', 
                        borderRadius: '3px',
                        marginTop: '4px',
                        overflow: 'hidden'
                      }}>
                        <div style={{ 
                          width: `${value * 100}%`, 
                          height: '100%', 
                          background: '#2563eb',
                          borderRadius: '3px',
                          transition: 'width 0.5s ease'
                        }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Recommendations */}
            <div style={{ 
              padding: '16px', 
              background: '#eff6ff', 
              borderRadius: '8px',
              marginBottom: '16px'
            }}>
              <h3 style={{ marginTop: 0, fontSize: '16px' }}>
                💡 Recommendations
              </h3>
              <ul style={{ paddingLeft: '20px', marginBottom: 0 }}>
                {result.analysis.recommendations?.map((rec: string, i: number) => (
                  <li key={i} style={{ marginBottom: '6px', color: '#1e40af' }}>{rec}</li>
                ))}
              </ul>
            </div>

            {/* Comment */}
            {result.analysis.comment && (
              <div style={{ 
                padding: '12px', 
                background: '#fef3c7', 
                borderRadius: '8px',
                marginBottom: '16px',
                fontSize: '14px',
                color: '#92400e'
              }}>
                💬 {result.analysis.comment}
              </div>
            )}

            {/* Metadata */}
            <div style={{ 
              fontSize: '12px',
              color: '#6b7280',
              borderTop: '1px solid #e5e7eb',
              paddingTop: '12px'
            }}>
              <span>File: {result.metadata.filename}</span>
              <span style={{ marginLeft: '16px' }}>
                Duration: {result.metadata.duration_seconds.toFixed(2)}s
              </span>
              <span style={{ marginLeft: '16px' }}>
                Baseline: {result.baseline_used ? '✅ Used' : 'Default'}
              </span>
              {result.processing_time_ms && (
                <span style={{ marginLeft: '16px' }}>
                  Processing: {result.processing_time_ms.toFixed(0)}ms
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
