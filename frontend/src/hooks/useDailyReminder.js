import { useEffect, useRef } from 'react';

/**
 * Browser notifications at ~9:00 local time when enabled.
 */
export function useDailyReminder(studentId, enabled) {
  const lastFired = useRef('');

  useEffect(() => {
    if (!studentId || !enabled) return;

    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {});
    }

    const tick = () => {
      if (!('Notification' in window) || Notification.permission !== 'granted') return;
      const now = new Date();
      const key = `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}`;
      if (now.getHours() !== 9 || now.getMinutes() > 2) return;
      if (lastFired.current === key) return;
      lastFired.current = key;
      try {
        new Notification('LearnFlow', {
          body: 'Time for a short lesson — check your streak and tree.',
          tag: 'learnflow-daily',
        });
      } catch {
        /* ignore */
      }
    };

    const id = setInterval(tick, 60 * 1000);
    tick();
    return () => clearInterval(id);
  }, [studentId, enabled]);
}

