import { motion } from 'framer-motion';
import {
  Activity, Brain, Shield, TrendingUp, Clock, Zap,
  ChevronRight, HeartPulse, Stethoscope, BarChart3,
} from 'lucide-react';

const features = [
  {
    icon: Brain,
    title: 'LSTM Deep Learning',
    desc: 'Real-time sepsis risk prediction using Long Short-Term Memory neural networks trained on ICU patient data.',
    color: '#a78bfa',
  },
  {
    icon: TrendingUp,
    title: 'Continuous Monitoring',
    desc: 'Track patient vitals 24/7 with automated risk trajectory analysis and early warning detection.',
    color: '#00f2fe',
  },
  {
    icon: Shield,
    title: 'Clinical Decision Support',
    desc: 'AI-generated clinical summaries with SHAP explainability for transparent, evidence-based decisions.',
    color: '#34d399',
  },
  {
    icon: Clock,
    title: 'Early Intervention',
    desc: 'Detect sepsis hours before clinical manifestation, enabling proactive treatment protocols.',
    color: '#f97316',
  },
  {
    icon: BarChart3,
    title: 'Comprehensive Analytics',
    desc: 'Vital trend charts, lab result tracking, and risk trajectory visualization in one unified dashboard.',
    color: '#4f8ef7',
  },
  {
    icon: Zap,
    title: 'Instant Alerts',
    desc: 'Role-based alert routing with clinical acknowledgment workflows and audit trails.',
    color: '#ff0844',
  },
];

const stats = [
  { value: '94.2%', label: 'Model Sensitivity' },
  { value: '<6h', label: 'Early Detection' },
  { value: '0.942', label: 'AUC Score' },
  { value: '24/7', label: 'Monitoring' },
];

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] },
  }),
};

export default function HomePage({ onNavigateLogin }) {
  return (
    <div className="homepage">
      {/* ── Decorative Glows ── */}
      <div className="hp-glow hp-glow-1" />
      <div className="hp-glow hp-glow-2" />

      {/* ── Navigation Bar ── */}
      <nav className="hp-nav">
        <div className="hp-nav-left">
          <Activity size={22} className="header-logo-icon" />
          <span className="header-logo">SepsisAI</span>
        </div>
        <motion.button
          className="btn btn-primary"
          onClick={onNavigateLogin}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
        >
          Sign In
          <ChevronRight size={16} />
        </motion.button>
      </nav>

      {/* ── Hero ── */}
      <section className="hp-hero">
        <motion.div
          className="hp-hero-content"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="hp-hero-badge">
            <Zap size={13} />
            AI-Powered Clinical Intelligence
          </div>
          <h1 className="hp-hero-title">
            Predict Sepsis.<br />
            <span className="hp-hero-gradient">Save Lives.</span>
          </h1>
          <p className="hp-hero-desc">
            An advanced AI monitoring system that analyzes real-time ICU patient data
            to predict sepsis risk hours before clinical onset — empowering physicians
            and nurses with actionable, explainable intelligence.
          </p>
          <div className="hp-hero-actions">
            <motion.button
              className="btn btn-primary btn-lg"
              onClick={onNavigateLogin}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              <Stethoscope size={18} />
              Access Dashboard
            </motion.button>
            <motion.button
              className="btn btn-ghost btn-lg"
              onClick={onNavigateLogin}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              <HeartPulse size={18} />
              Nurse Station
            </motion.button>
          </div>
        </motion.div>

        {/* Hero visual - animated monitor */}
        <motion.div
          className="hp-hero-visual"
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="hp-monitor-card glass-card">
            <div className="hp-monitor-header">
              <div className="hp-monitor-dot critical" />
              <span>Patient: Sarah Mitchell — ICU-4A</span>
            </div>
            <div className="hp-monitor-score">
              <span className="hp-monitor-value">82%</span>
              <span className="hp-monitor-label">Sepsis Risk</span>
            </div>
            <div className="hp-monitor-vitals">
              <div className="hp-mv"><span className="hp-mv-label">HR</span><span className="hp-mv-val critical">118</span></div>
              <div className="hp-mv"><span className="hp-mv-label">SpO2</span><span className="hp-mv-val critical">89%</span></div>
              <div className="hp-mv"><span className="hp-mv-label">Temp</span><span className="hp-mv-val critical">39.4°</span></div>
              <div className="hp-mv"><span className="hp-mv-label">Lactate</span><span className="hp-mv-val critical">4.8</span></div>
            </div>
            <div className="hp-monitor-wave">
              <svg viewBox="0 0 200 40" preserveAspectRatio="none">
                <motion.path
                  d="M0,20 Q10,5 20,20 T40,20 T60,20 Q70,35 80,20 T100,20 T120,20 Q130,8 140,20 T160,20 T180,20 T200,20"
                  fill="none"
                  stroke="#ff0844"
                  strokeWidth="1.5"
                  strokeOpacity="0.6"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                />
              </svg>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ── Stats Bar ── */}
      <motion.section
        className="hp-stats"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.3 }}
      >
        {stats.map((s, i) => (
          <motion.div key={i} className="hp-stat" custom={i} variants={fadeUp}>
            <div className="hp-stat-value">{s.value}</div>
            <div className="hp-stat-label">{s.label}</div>
          </motion.div>
        ))}
      </motion.section>

      {/* ── Features ── */}
      <section className="hp-features">
        <motion.div
          className="hp-section-header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <h2>Intelligent ICU Monitoring</h2>
          <p>Built on cutting-edge AI research for critical care environments</p>
        </motion.div>

        <div className="hp-feature-grid">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={i}
                className="glass-card hp-feature-card"
                custom={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, amount: 0.2 }}
                variants={fadeUp}
                whileHover={{ y: -4, borderColor: `${f.color}33` }}
              >
                <div className="hp-feature-icon" style={{ background: `${f.color}15`, color: f.color }}>
                  <Icon size={22} />
                </div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* ── Role Panels ── */}
      <section className="hp-roles">
        <motion.div
          className="hp-section-header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <h2>Role-Based Dashboards</h2>
          <p>Tailored views for each member of the clinical team</p>
        </motion.div>

        <div className="hp-roles-grid">
          <motion.div
            className="glass-card hp-role-panel"
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <div className="hp-role-icon physician-bg">
              <Stethoscope size={28} />
            </div>
            <h3>Physician Dashboard</h3>
            <ul>
              <li>Deep-dive patient analysis with AI reasoning</li>
              <li>SHAP feature importance & explainability</li>
              <li>24-hour vital trend tracking</li>
              <li>Clinical alert acknowledgment with notes</li>
              <li>NLP-generated clinical summaries</li>
            </ul>
            <motion.button
              className="btn btn-primary"
              style={{ marginTop: 'auto' }}
              onClick={onNavigateLogin}
              whileHover={{ scale: 1.02 }}
            >
              Physician Login <ChevronRight size={15} />
            </motion.button>
          </motion.div>

          <motion.div
            className="glass-card hp-role-panel"
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15 }}
          >
            <div className="hp-role-icon nurse-bg">
              <HeartPulse size={28} />
            </div>
            <h3>Nurse Station</h3>
            <ul>
              <li>Unit-level patient overview sorted by severity</li>
              <li>Quick vital signs at a glance</li>
              <li>Lab result entry (manual & PDF upload)</li>
              <li>Real-time LSTM risk trend charts</li>
              <li>Alert triage & acknowledgment</li>
            </ul>
            <motion.button
              className="btn btn-primary"
              style={{ marginTop: 'auto' }}
              onClick={onNavigateLogin}
              whileHover={{ scale: 1.02 }}
            >
              Nurse Login <ChevronRight size={15} />
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="hp-footer">
        <div className="hp-footer-left">
          <Activity size={18} className="header-logo-icon" />
          <span className="header-logo" style={{ fontSize: '1rem' }}>SepsisAI</span>
        </div>
        <p>AI-Driven ICU Monitoring System · Research Prototype</p>
      </footer>
    </div>
  );
}
