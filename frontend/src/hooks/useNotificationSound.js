import { useCallback, useRef } from 'react';

/**
 * Hook that plays a notification sound when called.
 * Sound is controlled by localStorage 'soundNotifications' setting.
 * Uses the Web Audio API so no external files are needed.
 */
export function useNotificationSound() {
  const audioCtxRef = useRef(null);

  const playSound = useCallback(() => {
    const enabled = localStorage.getItem('soundNotifications') !== 'false';
    if (!enabled) return;

    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      const ctx = audioCtxRef.current;

      // Two-tone alert beep
      const playTone = (freq, startTime, duration) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, startTime);
        gain.gain.setValueAtTime(0.15, startTime);
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(startTime);
        osc.stop(startTime + duration);
      };

      const now = ctx.currentTime;
      playTone(880, now, 0.15);       // A5
      playTone(1100, now + 0.18, 0.2); // ~C#6
    } catch (e) {
      // Audio not supported — silently fail
    }
  }, []);

  const isSoundEnabled = () => localStorage.getItem('soundNotifications') !== 'false';
  const toggleSound = () => {
    const current = isSoundEnabled();
    localStorage.setItem('soundNotifications', current ? 'false' : 'true');
    return !current;
  };

  return { playSound, isSoundEnabled, toggleSound };
}
