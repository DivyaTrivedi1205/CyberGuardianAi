import React, { useState } from 'react';
import { scorePassword, generatePassword, getPasswordSuggestions } from '../utils/helpers';
import { apiRequest, AUTH_TOKEN_KEY } from '../api/client';

export function PasswordAnalyzer({ onReturn, onFetchHistory, scanHistory }) {
  const [analyzerInput, setAnalyzerInput] = useState('');
  const [analyzerResult, setAnalyzerResult] = useState(null);
  const [isScanningPassword, setIsScanningPassword] = useState(false);
  const [generatedPassword, setGeneratedPassword] = useState('');

  const runPasswordAnalyzer = async () => {
    if (!analyzerInput.trim()) return;

    setIsScanningPassword(true);
    try {
      // apiRequest in client.js automatically attaches the Bearer token
      const result = await apiRequest('/security/analyze-password', {
        method: 'POST',
        body: JSON.stringify({ password: analyzerInput }),
      });
      setAnalyzerResult(result);

      const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
      if (token && onFetchHistory) {
        onFetchHistory(token);
      }
    } catch (error) {
      console.warn('Backend unavailable, falling back to local analysis');
      const result = scorePassword(analyzerInput);
      setAnalyzerResult({
        score: result.score,
        strength: result.grade,
        feedback: result.feedback,
        recommendations: [],
        suggestions: getPasswordSuggestions(analyzerInput),
        patterns_detected: []
      });
    } finally {
      setIsScanningPassword(false);
    }
  };

  const handleGeneratePassword = () => {
    const pwd = generatePassword(16);
    setGeneratedPassword(pwd);
    setAnalyzerInput(pwd);
  };

  return (
    <div className="analyzer-page-view">
      <header className="topbar">
        <div>
          <p className="eyebrow">Security tools</p>
          <h2>Password Strength Analyzer</h2>
        </div>
        <button type="button" className="primary-button" onClick={onReturn}>
          Back to dashboard
        </button>
      </header>

      <section className="hero-card">
        <div>
          <p className="eyebrow">Check Password Strength</p>
          <h3>Measure entropy, detect patterns, and find weaknesses.</h3>
          <p className="hero-copy">
            Our machine-learning heuristics detect dictionary words, repetitive sequencing, and known compromised patterns not just character counting.
          </p>
        </div>
      </section>

      <section className="analyzer-grid">
        <article className="panel analyzer-form-card">
          <p className="eyebrow">Password Scanner</p>
          <h3>Enter a password to test</h3>

          <label className="field-label" htmlFor="password-input">Password string</label>
          <input
            id="password-input"
            type="text"
            className="password-input"
            value={analyzerInput}
            onChange={(e) => setAnalyzerInput(e.target.value)}
            placeholder="e.g. CorrectHorseBatteryStaple"
            autoComplete="off"
            spellCheck="false"
          />

          <div className="auth-actions">
            <button type="button" className="primary-button" onClick={runPasswordAnalyzer} disabled={isScanningPassword}>
              {isScanningPassword ? <span className="loading-spinner" /> : 'Analyze Security'}
            </button>
            <button type="button" className="secondary-button" onClick={handleGeneratePassword}>
              Generate Secure
            </button>
          </div>
        </article>

        <article className="panel analyzer-result-card">
          <p className="eyebrow">Risk Classification</p>
          <h3>{analyzerResult ? `${analyzerResult.strength}` : 'No scan run yet'}</h3>

          {analyzerResult ? (
            <>
              <div className="score-row analyzer-score-row">
                <div>
                  <p className="score-label">Strength score</p>
                  <strong className="score-value">{analyzerResult.score}/100</strong>
                </div>
                <div className="score-meter">
                  <span style={{
                    width: `${analyzerResult.score}%`,
                    background: analyzerResult.score >= 80 ? '#22c55e' : analyzerResult.score >= 50 ? '#f59e0b' : '#ef4444'
                  }} />
                </div>
              </div>

              {analyzerResult.unified_assessment && (
                <div className="unified-assessment-box" style={{ marginTop: '15px', padding: '10px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px' }}>
                  <p className="score-label" style={{ fontWeight: 'bold' }}>Unified Backend Evaluation:</p>
                  <strong style={{ color: analyzerResult.unified_assessment.score >= 70 ? '#ef4444' : '#22c55e' }}>
                    {analyzerResult.unified_assessment.category}
                  </strong>
                  <p style={{ fontSize: '0.85rem', marginTop: '6px' }}>{analyzerResult.unified_assessment.meaning}</p>
                </div>
              )}

              <p className="score-label" style={{ marginTop: '16px' }}>Explainable risk signals:</p>
              <ul className="feedback-list">
                {analyzerResult.feedback && analyzerResult.feedback.length > 0 ?
                  analyzerResult.feedback.map((item, idx) => (
                    <li key={idx} style={{ color: analyzerResult.score < 50 ? '#fca5a5' : '#cbd5e1' }}>{item}</li>
                  )) : <li>No critical weaknesses found.</li>
                }
              </ul>

              {analyzerResult.recommendations && analyzerResult.recommendations.length > 0 && (
                <>
                  <p className="score-label" style={{ marginTop: '16px' }}>Recommendations:</p>
                  <ul className="feedback-list" style={{ color: '#93c5fd' }}>
                    {analyzerResult.recommendations.map((item, idx) => (
                      <li key={idx} style={{ color: '#93c5fd', borderLeft: '2px solid #3b82f6', paddingLeft: '8px', listStyleType: 'none', marginLeft: '-16px' }}>{item}</li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <p className="hero-copy">Enter a password above to begin analysis.</p>
          )}
        </article>
      </section>

      <section className="panel history-panel">
        <p className="eyebrow">Scan History</p>
        <h3>Previous Audits</h3>
        {scanHistory && scanHistory.length > 0 ? (
          <div className="history-list">
            {scanHistory.map((scan) => {
              const dateStr = new Date(scan.created_at * 1000).toLocaleString()
              return (
                <div key={scan.id} className="history-item">
                  <div className="history-meta">
                    <span className="history-text">Password ending in ***</span>
                    <span className="history-date">{dateStr}</span>
                  </div>
                  <div className="history-stats">
                    <span className={`status-pill status-${scan.grade ? scan.grade.toLowerCase() : 'unknown'}`}>{scan.grade}</span>
                    <span className="history-score">{scan.score}/100</span>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="hero-copy">No previous password audits found. Ensure you are signed in.</p>
        )}
      </section>
    </div>
  );
}