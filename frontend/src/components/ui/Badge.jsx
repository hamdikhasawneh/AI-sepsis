const variants = {
  default:   'bg-slate-800 text-slate-300 border-slate-700',
  critical:  'bg-rose-500/10 text-rose-400 border-rose-500/25',
  high:      'bg-orange-500/10 text-orange-400 border-orange-500/25',
  safe:      'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  info:      'bg-brand-500/10 text-brand-400 border-brand-500/25',
  warning:   'bg-amber-500/10 text-amber-400 border-amber-500/25',
};

export function Badge({ variant = 'default', className = '', children }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide uppercase border ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}

export function RiskBadge({ level, score }) {
  const v = level === 'critical' ? 'critical' : level === 'high' ? 'high' : 'safe';
  const dot = {
    critical: 'bg-rose-500 shadow-[0_0_6px_rgba(244,63,94,0.8)]',
    high:     'bg-orange-500 shadow-[0_0_6px_rgba(249,115,22,0.8)]',
    safe:     'bg-emerald-500',
  }[v];
  return (
    <Badge variant={v}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot} inline-block`} />
      {score != null ? `${score}%` : level}
    </Badge>
  );
}
