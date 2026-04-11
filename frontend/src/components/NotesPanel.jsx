import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Send, Stethoscope, HeartPulse } from 'lucide-react';

export default function NotesPanel({ patientId, patientName, notes, onAddNote, currentRole }) {
  const [text, setText] = useState('');
  const scrollRef = useRef(null);

  const patientNotes = notes
    .filter(n => n.patientId === patientId)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [patientNotes.length]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    onAddNote({
      id: `N-${Date.now()}`,
      patientId,
      author: currentRole === 'physician' ? 'Dr. James Rivera' : 'Nurse Station A',
      role: currentRole === 'physician' ? 'physician' : 'nurse',
      text: text.trim(),
      timestamp: new Date().toISOString(),
    });
    setText('');
  };

  return (
    <div className="notes-panel">
      <div className="notes-header">
        <MessageSquare size={16} className="notes-header-icon" />
        <h4>Clinical Notes — {patientName}</h4>
        <span className="notes-count">{patientNotes.length}</span>
      </div>

      <div className="notes-feed" ref={scrollRef}>
        {patientNotes.length === 0 ? (
          <div className="notes-empty">
            <MessageSquare size={24} style={{ opacity: 0.15, marginBottom: 6 }} />
            <p>No notes yet for this patient</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {patientNotes.map(note => (
              <motion.div
                key={note.id}
                className={`note-bubble ${note.role}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
              >
                <div className="note-bubble-header">
                  <div className="note-author">
                    {note.role === 'physician'
                      ? <Stethoscope size={12} className="note-role-icon physician" />
                      : <HeartPulse size={12} className="note-role-icon nurse" />
                    }
                    <span className="note-author-name">{note.author}</span>
                    <span className={`note-role-badge ${note.role}`}>
                      {note.role === 'physician' ? 'MD' : 'RN'}
                    </span>
                  </div>
                  <span className="note-time">
                    {new Date(note.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <p className="note-text">{note.text}</p>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      <form className="notes-input" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder={`Add a ${currentRole === 'physician' ? 'physician' : 'nursing'} note...`}
          value={text}
          onChange={e => setText(e.target.value)}
        />
        <motion.button
          type="submit"
          className="notes-send-btn"
          disabled={!text.trim()}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Send size={16} />
        </motion.button>
      </form>
    </div>
  );
}
