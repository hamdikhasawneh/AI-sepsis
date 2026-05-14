export function Input({ label, error, icon: Icon, rightEl, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</label>}
      <div className="relative flex items-center">
        {Icon && <Icon size={15} className="absolute left-3 text-slate-500 pointer-events-none" />}
        <input
          className={`w-full bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-600
            focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/30 transition-all
            ${Icon ? 'pl-9' : 'pl-3.5'} ${rightEl ? 'pr-10' : 'pr-3.5'} py-2.5 ${className}`}
          {...props}
        />
        {rightEl && <div className="absolute right-3">{rightEl}</div>}
      </div>
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  );
}

export function Select({ label, className = '', children, ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</label>}
      <select
        className={`w-full bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200
          focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/30 transition-all
          px-3.5 py-2.5 cursor-pointer appearance-none ${className}`}
        {...props}
      >
        {children}
      </select>
    </div>
  );
}

export function Textarea({ label, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</label>}
      <textarea
        className={`w-full bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-600
          focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/30 transition-all
          px-3.5 py-3 resize-none ${className}`}
        {...props}
      />
    </div>
  );
}
