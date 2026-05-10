import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';

export function Modal({ open, onClose, title, children, size = 'md' }) {
  const widths = { sm: 'max-w-md', md: 'max-w-2xl', lg: 'max-w-4xl', xl: 'max-w-6xl' };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="absolute inset-0 bg-void-950/80 backdrop-blur-sm" onClick={onClose} />
          <motion.div
            className={`relative z-10 w-full ${widths[size]} bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl`}
            initial={{ opacity: 0, scale: 0.94, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 16 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <h2 className="text-base font-semibold text-slate-100">{title}</h2>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
