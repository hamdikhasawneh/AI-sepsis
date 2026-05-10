export function TabList({ tabs, active, onChange, className = '' }) {
  return (
    <div className={`flex gap-0.5 bg-slate-900 border border-slate-800 rounded-lg p-1 ${className}`}>
      {tabs.map(t => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`flex-1 px-3.5 py-2 rounded-md text-sm font-medium transition-all duration-200 whitespace-nowrap
            ${active === t.key
              ? 'bg-slate-800 text-slate-100 shadow-sm'
              : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'}`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
