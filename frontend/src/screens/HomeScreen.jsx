import { useRef, useEffect } from "react";
import { motion, useScroll, useTransform, useInView } from "framer-motion";
import {
  Activity,
  Brain,
  Shield,
  TrendingUp,
  Clock,
  Zap,
  ChevronRight,
  HeartPulse,
  Stethoscope,
  BarChart3,
  ArrowRight,
  Sparkles,
  GitBranch,
  Lock,
} from "lucide-react";

/* ─── Animation helpers ─── */
const easeOut = [0.16, 1, 0.3, 1];

function FadeUp({ children, delay = 0, className = "" }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ opacity: 0, y: 28 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.65, delay, ease: easeOut }}
    >
      {children}
    </motion.div>
  );
}

/* ─── Static data ─── */
const stats = [
  { value: "69.7%", label: "Sensitivity", detail: "True positive rate" },
  { value: "81.31%", label: "Specificity", detail: "True negative rate" },
  { value: "0.7957", label: "AUROC", detail: "Model discrimination" },
  { value: "82.7%", label: "Early Warning", detail: "Alerts ≥6h before onset" },
  { value: "12 hr", label: "Risk Horizon", detail: "Prediction window" },
];

const features = [
  {
    icon: Brain,
    color: "#818CF8",
    bg: "from-indigo-500/10 to-violet-500/5",
    title: "Dynamic Survival Transformer",
    desc: "A 3-layer, 8-head attention model trained on sequential ICU vital signals. 127 clinical features, 48-bin probability mass output.",
  },
  {
    icon: Zap,
    color: "#F472B6",
    bg: "from-pink-500/10 to-rose-500/5",
    title: "Real-Time Risk Updates",
    desc: "Every new vital reading triggers an inference pass. Risk scores update continuously, not on a fixed schedule.",
  },
  {
    icon: Shield,
    color: "#34D399",
    bg: "from-emerald-500/10 to-teal-500/5",
    title: "SHAP Attribution",
    desc: "GradientSHAP attributions precomputed per stay. Physicians see exactly which vitals are driving the predicted risk.",
  },
  {
    icon: TrendingUp,
    color: "#60A5FA",
    bg: "from-blue-500/10 to-sky-500/5",
    title: "24-Hour Trajectory",
    desc: "Full risk history charted per patient. Spot trends at a glance — rising, stable, or resolving sepsis risk.",
  },
  {
    icon: Clock,
    color: "#FBBF24",
    bg: "from-amber-500/10 to-yellow-500/5",
    title: "Early Intervention",
    desc: "Detect deterioration 6–12 hours before clinical manifestation, while treatment options are still at their widest.",
  },
  {
    icon: BarChart3,
    color: "#A78BFA",
    bg: "from-violet-500/10 to-purple-500/5",
    title: "Lab & Vital Analytics",
    desc: "Unified view of vital trends, lab values, and AI risk scores across your entire unit — one screen, zero context-switching.",
  },
];

const roles = [
  {
    icon: Stethoscope,
    accent: "#60A5FA",
    glow: "rgba(96,165,250,0.15)",
    ring: "from-blue-500/20 to-indigo-500/10",
    title: "Physician Dashboard",
    sub: "Clinical intelligence, full explainability",
    items: [
      "DST v2 risk score with 12-hour horizon",
      "SHAP feature attribution per patient",
      "Vital trend charts with reference bands",
      "NLP-generated clinical risk summary",
      "Alert acknowledgment with audit trail",
    ],
  },
  {
    icon: HeartPulse,
    accent: "#34D399",
    glow: "rgba(52,211,153,0.15)",
    ring: "from-emerald-500/20 to-teal-500/10",
    title: "Nurse Station",
    sub: "Unit overview, task & lab management",
    items: [
      "Unit-level patient table sorted by severity",
      "Live vitals with abnormal highlighting",
      "Manual lab entry or PDF upload + OCR",
      "Shift task list with completion tracking",
      "Read-only alerts, escalate to physician",
    ],
  },
];

/* ─── ECG canvas waveform ─── */
function buildBeatLookup() {
  const BW = 80;
  const out = new Float32Array(BW);
  const bez = (p0, p1, p2, p3, t) =>
    (1 - t) ** 3 * p0 +
    3 * (1 - t) ** 2 * t * p1 +
    3 * (1 - t) * t ** 2 * p2 +
    t ** 3 * p3;
  for (let px = 0; px < BW; px++) {
    if (px < 10) out[px] = 24;
    else if (px < 18) out[px] = bez(24, 24, 19, 19, (px - 10) / 8);
    else if (px < 26) out[px] = bez(19, 19, 24, 24, (px - 18) / 8);
    else if (px < 31) out[px] = 24;
    else if (px < 35) out[px] = 24 + ((27 - 24) * (px - 31)) / 4;
    else if (px < 39) out[px] = 27 + ((4 - 27) * (px - 35)) / 4;
    else if (px < 42) out[px] = 4 + ((35 - 4) * (px - 39)) / 3;
    else if (px < 46) out[px] = 35 + ((24 - 35) * (px - 42)) / 4;
    else if (px < 53) out[px] = 24;
    else if (px < 62) out[px] = bez(24, 24, 18, 18, (px - 53) / 9);
    else if (px < 71) out[px] = bez(18, 18, 24, 24, (px - 62) / 9);
    else out[px] = 24;
  }
  return out;
}
const BEAT = buildBeatLookup();
const WAVE_LEN = 800; // 10 beats
const WAVE_Y = new Float32Array(WAVE_LEN);
for (let i = 0; i < WAVE_LEN; i++) WAVE_Y[i] = BEAT[i % 80];

function EcgCanvas() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const W = 400,
      H = 48;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    let headX = 0;
    let raf;
    const SPEED = WAVE_LEN / (15 * 60); // 10s loop at 60fps

    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      ctx.beginPath();
      for (let sx = 0; sx < W; sx++) {
        const y = WAVE_Y[(Math.floor(headX) + sx) % WAVE_LEN];
        sx === 0 ? ctx.moveTo(sx, y) : ctx.lineTo(sx, y);
      }
      const grad = ctx.createLinearGradient(0, 0, W, 0);
      grad.addColorStop(0, "rgba(244,63,94,0)");
      grad.addColorStop(0.08, "rgba(244,63,94,0.85)");
      grad.addColorStop(0.92, "rgba(244,63,94,0.85)");
      grad.addColorStop(1, "rgba(244,63,94,0)");
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.5;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.stroke();

      // glowing tip at right edge
      const tipY = WAVE_Y[(Math.floor(headX) + W - 1) % WAVE_LEN];
      const glow = ctx.createRadialGradient(W - 1, tipY, 0, W - 1, tipY, 5);
      glow.addColorStop(0, "rgba(244,63,94,0.9)");
      glow.addColorStop(0.4, "rgba(244,63,94,0.4)");
      glow.addColorStop(1, "rgba(244,63,94,0)");
      ctx.beginPath();
      ctx.arc(W - 1, tipY, 5, 0, Math.PI * 2);
      ctx.fillStyle = glow;
      ctx.fill();

      headX = (headX + SPEED) % WAVE_LEN;
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, []);

  return <canvas ref={canvasRef} style={{ width: "100%", height: "100%" }} />;
}

/* ─── Live monitor card ─── */
function MonitorCard() {
  return (
    <div className="relative">
      {/* Glow behind card */}
      <div className="absolute inset-0 bg-rose-500/10 blur-3xl rounded-full scale-75" />

      <motion.div
        className="relative bg-slate-900 border border-slate-700/60 rounded-2xl overflow-hidden shadow-2xl shadow-black/50"
        initial={{ opacity: 0, y: 24, rotateX: 8 }}
        animate={{ opacity: 1, y: 0, rotateX: 0 }}
        transition={{ duration: 0.9, delay: 0.35, ease: easeOut }}
        style={{ transformPerspective: 1200 }}
      >
        {/* Top accent line */}
        <div className="h-px bg-gradient-to-r from-transparent via-rose-500/50 to-transparent" />

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
              <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
              <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
            </div>
            <span className="text-xs text-slate-500 font-medium">
              ARISE — ICU Monitor
            </span>
          </div>
          <div className="flex items-center gap-1.5 bg-rose-500/12 border border-rose-500/25 px-2.5 py-1 rounded-full">
            <motion.span
              className="w-1.5 h-1.5 rounded-full bg-rose-500"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
            <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider">
              Critical
            </span>
          </div>
        </div>

        {/* Patient info */}
        <div className="px-5 py-4">
          <div className="flex items-start justify-between mb-5">
            <div>
              <p className="text-[11px] text-slate-500 uppercase tracking-widest mb-0.5">
                Patient
              </p>
              <h3 className="text-base font-bold text-slate-100">
                Sarah Mitchell
              </h3>
              <p className="text-xs text-slate-500">ICU-4A · 58 y/o · Female</p>
            </div>
            <div className="text-right">
              <motion.div
                className="text-5xl font-mono font-black text-rose-400 leading-none"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.8 }}
              >
                82%
              </motion.div>
              <p className="text-[10px] text-slate-500 mt-1">
                Sepsis Risk · 12 hr
              </p>
            </div>
          </div>

          {/* Vitals grid */}
          <div className="grid grid-cols-4 gap-2 mb-4">
            {[
              { l: "HR", v: "118", u: "bpm", ab: true },
              { l: "SpO2", v: "89", u: "%", ab: true },
              { l: "Temp", v: "39.4", u: "°C", ab: true },
              { l: "Lactate", v: "4.8", u: "mmol", ab: true },
            ].map(({ l, v, u, ab }, i) => (
              <motion.div
                key={l}
                className="bg-rose-500/6 border border-rose-500/15 rounded-xl p-3 text-center"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.9 + i * 0.08, ease: easeOut }}
              >
                <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">
                  {l}
                </p>
                <p className="text-sm font-mono font-bold text-rose-400">{v}</p>
                <p className="text-[8px] text-slate-600">{u}</p>
              </motion.div>
            ))}
          </div>

          {/* Waveform */}
          <div className="bg-slate-950/60 rounded-xl p-0 h-16 overflow-hidden">
            <EcgCanvas />
          </div>
        </div>

        {/* SHAP mini */}
        <div className="px-5 pb-5">
          <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest mb-3">
            Top Risk Drivers
          </p>
          {[
            { name: "Lactate", pct: 82 },
            { name: "Heart Rate", pct: 65 },
            { name: "SpO₂", pct: 48 },
          ].map(({ name, pct }, i) => (
            <motion.div
              key={name}
              className="flex items-center gap-3 mb-2"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 1.4 + i * 0.1, ease: easeOut }}
            >
              <span className="text-[10px] text-slate-400 w-20 flex-shrink-0">
                {name}
              </span>
              <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-rose-500 to-orange-500 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{
                    delay: 1.6 + i * 0.1,
                    duration: 0.7,
                    ease: easeOut,
                  }}
                />
              </div>
              <span className="text-[10px] font-mono text-rose-400 w-8 text-right">
                +{pct}%
              </span>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

/* ─── Main ─── */
export default function HomeScreen({ onNavigateLogin }) {
  const heroRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, 60]);
  const heroOp = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  return (
    <div className="min-h-screen bg-void-950 text-slate-200 overflow-x-hidden">
      {/* ── Nav ── */}
      <nav className="fixed top-0 inset-x-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-brand-600 rounded-lg flex items-center justify-center shadow-lg shadow-brand-600/40">
              <Activity size={14} className="text-white" strokeWidth={2.5} />
            </div>
            <span className="font-bold text-slate-100 tracking-tight">
              ARISE
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onNavigateLogin}
              className="hidden sm:flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
            >
              Sign in
            </button>
            <button
              onClick={onNavigateLogin}
              className="flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-all shadow-lg shadow-brand-600/30 hover:shadow-brand-500/40"
            >
              Get Started <ArrowRight size={14} />
            </button>
          </div>
        </div>
        {/* Nav glass blur */}
        <div className="absolute inset-0 -z-10 bg-void-950/70 backdrop-blur-xl border-b border-slate-800/40" />
      </nav>

      {/* ── Hero ── */}
      <section
        ref={heroRef}
        className="relative min-h-screen flex items-center pt-14"
      >
        {/* Background */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {/* Grid */}
          <div
            className="absolute inset-0"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
              backgroundSize: "40px 40px",
            }}
          />
          {/* Radial fade */}
          <div
            className="absolute inset-0 bg-gradient-radial from-transparent via-transparent to-void-950"
            style={{
              background:
                "radial-gradient(ellipse 80% 50% at 50% 40%, rgba(59,130,246,0.06) 0%, transparent 70%)",
            }}
          />
          {/* Glow orbs */}
          <motion.div
            className="absolute top-1/4 right-1/3 w-[600px] h-[600px] rounded-full blur-[120px] opacity-30"
            style={{
              background:
                "radial-gradient(circle, rgba(59,130,246,0.3) 0%, transparent 70%)",
            }}
            animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.5, 0.3] }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] rounded-full blur-[100px] opacity-20"
            style={{
              background:
                "radial-gradient(circle, rgba(124,58,237,0.4) 0%, transparent 70%)",
            }}
            animate={{ scale: [1, 1.15, 1], opacity: [0.2, 0.35, 0.2] }}
            transition={{
              duration: 10,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 3,
            }}
          />
        </div>

        <motion.div
          style={{ y: heroY, opacity: heroOp }}
          className="relative z-10 w-full max-w-6xl mx-auto px-6 py-24"
        >
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            {/* Left */}
            <div>
              <motion.div
                className="inline-flex items-center gap-2 bg-slate-800/80 border border-slate-700/60 text-slate-400 px-3.5 py-1.5 rounded-full text-xs font-medium mb-8 backdrop-blur-sm"
                initial={{ opacity: 0, y: -12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: easeOut }}
              >
                <Sparkles size={11} className="text-brand-400" />
                Dynamic Survival Transformer · v2
                <span className="w-px h-3 bg-slate-700" />
                <span className="text-brand-400">New</span>
              </motion.div>

              <motion.h1
                className="text-[3.6rem] leading-[1.05] font-black tracking-tight text-slate-50 mb-6"
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.1, ease: easeOut }}
              >
                Predict Sepsis.
                <br />
                <span className="relative">
                  <span className="bg-gradient-to-r from-blue-400 via-violet-400 to-pink-400 bg-clip-text text-transparent">
                    Save Lives.
                  </span>
                  <motion.span
                    className="absolute -bottom-1 left-0 right-0 h-px bg-gradient-to-r from-blue-400/60 via-violet-400/60 to-pink-400/60"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.8, delay: 0.8, ease: easeOut }}
                    style={{ transformOrigin: "left" }}
                  />
                </span>
              </motion.h1>

              <motion.p
                className="text-lg text-slate-400 leading-relaxed mb-10 max-w-lg"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.25, ease: easeOut }}
              >
                An AI monitoring system that analyzes real-time ICU vitals to
                predict sepsis risk hours before clinical onset — with full
                explainability for your clinical team.
              </motion.p>

              <motion.div
                className="flex flex-wrap gap-3 mb-10"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.35, ease: easeOut }}
              >
                <button
                  onClick={onNavigateLogin}
                  className="group flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white font-semibold px-6 py-3 rounded-xl transition-all shadow-xl shadow-brand-600/25 hover:shadow-brand-500/40 hover:-translate-y-0.5"
                >
                  <Stethoscope size={18} />
                  Physician Dashboard
                  <ChevronRight
                    size={15}
                    className="opacity-60 group-hover:translate-x-0.5 transition-transform"
                  />
                </button>
                <button
                  onClick={onNavigateLogin}
                  className="group flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 text-slate-200 font-semibold px-6 py-3 rounded-xl transition-all hover:-translate-y-0.5"
                >
                  <HeartPulse size={18} className="text-emerald-400" />
                  Nurse Station
                </button>
              </motion.div>

              {/* Trust badges */}
              <motion.div
                className="flex flex-wrap items-center gap-4 text-xs text-slate-600"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.6 }}
              >
                {[
                  { icon: Lock, text: "JWT Auth" },
                  { icon: GitBranch, text: "FastAPI + PyTorch" },
                  { icon: Shield, text: "Platt Calibrated" },
                ].map(({ icon: Icon, text }) => (
                  <div key={text} className="flex items-center gap-1.5">
                    <Icon size={11} />
                    <span>{text}</span>
                  </div>
                ))}
              </motion.div>
            </div>

            {/* Right — monitor card */}
            <MonitorCard />
          </div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2 }}
        >
          <motion.div
            className="w-px h-12 bg-gradient-to-b from-transparent via-slate-600 to-transparent"
            animate={{ scaleY: [0.5, 1, 0.5], opacity: [0.3, 0.8, 0.3] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        </motion.div>
      </section>

      {/* ── Stats ── */}
      <section className="relative py-20 border-y border-slate-800/60">
        <div className="absolute inset-0 bg-gradient-to-b from-slate-900/30 to-transparent pointer-events-none" />
        <div className="relative max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-8">
            {stats.map((s, i) => (
              <FadeUp key={i} delay={i * 0.1}>
                <div className="text-center">
                  <div className="text-4xl font-mono font-black text-slate-50 mb-1 tracking-tight">
                    {s.value}
                  </div>
                  <div className="text-sm font-semibold text-slate-300 mb-0.5">
                    {s.label}
                  </div>
                  <div className="text-xs text-slate-600">{s.detail}</div>
                </div>
              </FadeUp>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="py-28 max-w-6xl mx-auto px-6">
        <FadeUp className="text-center mb-16">
          <p className="text-xs font-semibold text-brand-400 uppercase tracking-widest mb-3">
            Capabilities
          </p>
          <h2 className="text-4xl font-black text-slate-50 tracking-tight mb-4">
            Built for critical care
          </h2>
          <p className="text-slate-500 max-w-xl mx-auto leading-relaxed">
            State-of-the-art AI paired with a clinical workflow designed around
            how your team actually works
          </p>
        </FadeUp>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <FadeUp key={i} delay={i * 0.07}>
                <div className="group relative h-full p-5 rounded-2xl border border-slate-800 hover:border-slate-700 bg-slate-900/50 hover:bg-slate-900 transition-all duration-300 cursor-default overflow-hidden">
                  {/* Hover glow */}
                  <div
                    className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-2xl"
                    style={{
                      background: `radial-gradient(circle at 30% 40%, ${f.color}08 0%, transparent 60%)`,
                    }}
                  />
                  <div
                    className={`w-10 h-10 rounded-xl mb-4 flex items-center justify-center bg-gradient-to-br ${f.bg} border border-slate-800`}
                  >
                    <Icon size={18} style={{ color: f.color }} />
                  </div>
                  <h3 className="text-sm font-bold text-slate-200 mb-2">
                    {f.title}
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    {f.desc}
                  </p>
                </div>
              </FadeUp>
            );
          })}
        </div>
      </section>

      {/* ── Role panels ── */}
      <section className="py-28 bg-slate-900/30 border-y border-slate-800/60">
        <div className="max-w-6xl mx-auto px-6">
          <FadeUp className="text-center mb-16">
            <p className="text-xs font-semibold text-brand-400 uppercase tracking-widest mb-3">
              Dashboards
            </p>
            <h2 className="text-4xl font-black text-slate-50 tracking-tight mb-4">
              Role-based access
            </h2>
            <p className="text-slate-500">
              Tailored for each member of the clinical team
            </p>
          </FadeUp>

          <div className="grid md:grid-cols-2 gap-6">
            {roles.map((r, i) => {
              const Icon = r.icon;
              return (
                <FadeUp key={i} delay={i * 0.15}>
                  <div className="relative h-full rounded-2xl border border-slate-800 bg-slate-900 p-7 overflow-hidden group hover:border-slate-700 transition-colors">
                    {/* Corner glow */}
                    <div
                      className="absolute top-0 right-0 w-48 h-48 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"
                      style={{
                        background: r.glow,
                        transform: "translate(30%, -30%)",
                      }}
                    />
                    {/* Top gradient line */}
                    <div
                      className="absolute top-0 left-8 right-8 h-px"
                      style={{
                        background: `linear-gradient(90deg, transparent, ${r.accent}40, transparent)`,
                      }}
                    />

                    <div className="relative">
                      <div
                        className={`w-12 h-12 rounded-2xl mb-5 flex items-center justify-center bg-gradient-to-br ${r.ring}`}
                        style={{ border: `1px solid ${r.accent}20` }}
                      >
                        <Icon size={22} style={{ color: r.accent }} />
                      </div>

                      <h3 className="text-xl font-bold text-slate-100 mb-1">
                        {r.title}
                      </h3>
                      <p className="text-sm text-slate-500 mb-6">{r.sub}</p>

                      <ul className="space-y-2.5 mb-8">
                        {r.items.map((item, j) => (
                          <li
                            key={j}
                            className="flex items-start gap-2.5 text-sm text-slate-400"
                          >
                            <span
                              className="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                              style={{
                                background: `${r.accent}15`,
                                border: `1px solid ${r.accent}25`,
                              }}
                            >
                              <span
                                className="w-1 h-1 rounded-full"
                                style={{ background: r.accent }}
                              />
                            </span>
                            {item}
                          </li>
                        ))}
                      </ul>

                      <button
                        onClick={onNavigateLogin}
                        className="flex items-center gap-2 text-sm font-semibold transition-all hover:-translate-y-0.5"
                        style={{ color: r.accent }}
                      >
                        Access dashboard <ArrowRight size={15} />
                      </button>
                    </div>
                  </div>
                </FadeUp>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-28 max-w-6xl mx-auto px-6">
        <FadeUp>
          <div className="relative rounded-3xl border border-slate-800 bg-slate-900 p-16 text-center overflow-hidden">
            {/* Background */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background:
                  "radial-gradient(ellipse 70% 60% at 50% 50%, rgba(59,130,246,0.06) 0%, transparent 70%)",
              }}
            />
            <div className="absolute top-0 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-brand-500/40 to-transparent" />

            <div className="relative">
              <div className="inline-flex items-center justify-center w-14 h-14 bg-brand-600/10 border border-brand-500/20 rounded-2xl mb-6">
                <Activity size={24} className="text-brand-400" />
              </div>
              <h2 className="text-4xl font-black text-slate-50 tracking-tight mb-4">
                Ready to protect your patients?
              </h2>
              <p className="text-slate-500 mb-8 max-w-lg mx-auto">
                Access the live demo with pre-seeded ICU patients, real DST v2
                predictions, and full clinical workflow.
              </p>
              <button
                onClick={onNavigateLogin}
                className="inline-flex items-center gap-2.5 bg-brand-600 hover:bg-brand-500 text-white font-bold px-8 py-4 rounded-xl transition-all shadow-2xl shadow-brand-600/30 hover:shadow-brand-500/40 hover:-translate-y-0.5 text-base"
              >
                <Activity size={20} />
                Launch Demo
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        </FadeUp>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-slate-800/60 py-8">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-brand-600 rounded-md flex items-center justify-center">
              <Activity size={12} className="text-white" strokeWidth={2.5} />
            </div>
            <span className="text-sm font-bold text-slate-500">ARISE</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-slate-700">
            <span>AI-Driven ICU Monitoring</span>
            <span>·</span>
            <span>Research Prototype</span>
            <span>·</span>
            <span>DST v2 Model</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
