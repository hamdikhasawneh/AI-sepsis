const variants = {
  primary:   'bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-600/20 disabled:opacity-40 disabled:cursor-not-allowed',
  secondary: 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-slate-600',
  ghost:     'bg-transparent hover:bg-slate-800/60 text-slate-400 hover:text-slate-200',
  danger:    'bg-rose-600/10 hover:bg-rose-600/20 text-rose-400 border border-rose-600/30',
  outline:   'bg-transparent border border-slate-700 hover:border-brand-500 text-slate-300 hover:text-brand-400',
};

const sizes = {
  xs: 'px-2.5 py-1.5 text-xs gap-1.5',
  sm: 'px-3.5 py-2 text-sm gap-2',
  md: 'px-4 py-2.5 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2.5',
};

export function Button({ variant = 'primary', size = 'md', className = '', children, ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 whitespace-nowrap ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
