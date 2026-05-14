const RANGES = {
  hr:    { min: 60,   max: 100  },
  bpSys: { min: 90,   max: 140  },
  spo2:  { min: 95,   max: 100  },
  rr:    { min: 12,   max: 20   },
  temp:  { min: 36.0, max: 37.5 },
};

export function isAbnormal(key, val) {
  const r = RANGES[key];
  if (!r || val == null) return false;
  return val < r.min || val > r.max;
}

export function VitalCard({ icon: Icon, label, value, unit, vitalKey }) {
  const abnormal = isAbnormal(vitalKey, typeof value === 'number' ? value : parseFloat(value));
  return (
    <div className={`flex flex-col gap-2 p-4 rounded-xl border transition-all
      ${abnormal
        ? 'bg-rose-500/5 border-rose-500/20'
        : 'bg-slate-900 border-slate-800'}`}>
      <div className="flex items-center justify-between">
        <Icon size={15} className={abnormal ? 'text-rose-400' : 'text-slate-500'} />
        {abnormal && (
          <span className="text-[10px] font-semibold text-rose-400 uppercase tracking-wider">High</span>
        )}
      </div>
      <div>
        <div className={`text-2xl font-mono font-semibold leading-none ${abnormal ? 'text-rose-400' : 'text-slate-100'}`}>
          {value ?? '—'}
        </div>
        <div className="text-[11px] text-slate-500 mt-1">{label} · {unit}</div>
      </div>
    </div>
  );
}
