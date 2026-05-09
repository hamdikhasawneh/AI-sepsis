export function Spinner({ size = 'md', className = '' }) {
  const s = { sm: 'w-4 h-4 border-2', md: 'w-6 h-6 border-2', lg: 'w-8 h-8 border-[3px]' }[size];
  return (
    <div className={`${s} rounded-full border-slate-700 border-t-brand-500 animate-spin ${className}`} />
  );
}

export function PageLoader() {
  return (
    <div className="min-h-screen bg-void-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 rounded-full border-2 border-slate-800 border-t-brand-500 animate-spin" />
        <p className="text-sm text-slate-500">Loading...</p>
      </div>
    </div>
  );
}
