import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { getShapValues, getNlpSummary } from '../mockData';

export default function AcknowledgeModal({ alert, onClose, onConfirm }) {
  const [note, setNote] = useState('');

  if (!alert) return null;

  const shapData = getShapValues(alert.patientId).slice(0, 3);
  const nlpSummary = getNlpSummary(alert.patientId);
  const scoreColor =
    alert.level === 'critical'
      ? 'var(--risk-critical)'
      : alert.level === 'high'
      ? 'var(--risk-high)'
      : 'var(--accent-cyan)';

  return (
    <AnimatePresence>
      <motion.div
        className="modal-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="modal-content"
          initial={{ opacity: 0, scale: 0.92, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 20 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="modal-header">
            <h2>Clinical Alert Acknowledgment</h2>
            <button className="modal-close" onClick={onClose}>
              <X size={20} />
            </button>
          </div>

          {/* Body */}
          <div className="modal-body">
            {/* Left Side — Alert Details */}
            <div className="modal-left">
              <p className="modal-section-title">Alert Details</p>

              <div className="modal-alert-detail">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span
                    className="risk-pill"
                    style={{
                      background: alert.level === 'critical' ? 'var(--risk-critical-bg)' : 'var(--risk-high-bg)',
                      color: alert.level === 'critical' ? 'var(--risk-critical)' : 'var(--risk-high)',
                      border: `1px solid ${alert.level === 'critical' ? 'var(--risk-critical-border)' : 'var(--risk-high-border)'}`,
                      fontSize: '0.72rem',
                      padding: '3px 10px',
                    }}
                  >
                    {alert.level}
                  </span>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {alert.patientName} — {alert.bed}
                  </span>
                </div>

                <h4>{alert.title}</h4>
                <p>{alert.message}</p>
              </div>

              <p className="modal-section-title">Vital Snapshot</p>
              <div className="modal-snapshot-charts">
                <div className="glass-card modal-snapshot-card">
                  <div className="modal-snapshot-value" style={{ color: alert.vital_snapshot?.hr > 100 ? 'var(--risk-critical)' : 'var(--accent-cyan)' }}>
                    {alert.vital_snapshot?.hr || '—'}
                  </div>
                  <div className="modal-snapshot-label">Heart Rate (bpm)</div>
                </div>
                <div className="glass-card modal-snapshot-card">
                  <div className="modal-snapshot-value" style={{ color: alert.vital_snapshot?.bpSys < 90 ? 'var(--risk-critical)' : 'var(--accent-cyan)' }}>
                    {alert.vital_snapshot ? `${alert.vital_snapshot.bpSys}/${alert.vital_snapshot.bpDia}` : '—'}
                  </div>
                  <div className="modal-snapshot-label">Blood Pressure (mmHg)</div>
                </div>
              </div>
            </div>

            {/* Right Side — AI Rationale */}
            <div className="modal-right">
              <p className="modal-section-title">AI Rationale</p>

              <div className="modal-score-display">
                <span className="modal-score-value" style={{ color: scoreColor }}>
                  {alert.level === 'critical' ? '82' : alert.level === 'high' ? '55' : '28'}%
                </span>
                <span className="risk-pill" style={{
                  background: alert.level === 'critical' ? 'var(--risk-critical-bg)' : 'var(--risk-high-bg)',
                  color: alert.level === 'critical' ? 'var(--risk-critical)' : 'var(--risk-high)',
                  border: `1px solid ${alert.level === 'critical' ? 'var(--risk-critical-border)' : 'var(--risk-high-border)'}`,
                }}>
                  {alert.level} Risk
                </span>
              </div>

              <div className="nlp-summary-box" style={{ marginBottom: 20 }}>
                <h4>Model Analysis</h4>
                <p className="nlp-summary-text">{nlpSummary}</p>
              </div>

              <p className="modal-section-title">Top Contributing Factors</p>
              <div className="modal-shap-list">
                {shapData.map((item, i) => (
                  <div key={i} className="modal-shap-item">
                    <span className="modal-shap-feature">{item.feature}</span>
                    <span className={`modal-shap-impact ${item.direction}`}>
                      {item.direction === 'increase' ? '+' : '−'}{(item.impact * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="modal-footer">
            <textarea
              className="modal-textarea"
              placeholder="Enter your clinical action note (mandatory)..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <div className="modal-footer-actions">
              <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
              <button
                className="btn btn-primary"
                disabled={!note.trim()}
                onClick={() => { onConfirm(alert.id, note); setNote(''); }}
              >
                Confirm & Dismiss Alert
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
