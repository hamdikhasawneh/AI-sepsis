export function Card({ className = '', children, ...props }) {
  return (
    <div
      className={`bg-slate-900 border border-slate-800 rounded-xl ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className = '', children }) {
  return (
    <div className={`px-5 py-4 border-b border-slate-800 flex items-center justify-between ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ className = '', children }) {
  return (
    <h3 className={`text-sm font-semibold text-slate-200 tracking-tight ${className}`}>
      {children}
    </h3>
  );
}

export function CardBody({ className = '', children }) {
  return (
    <div className={`p-5 ${className}`}>
      {children}
    </div>
  );
}
