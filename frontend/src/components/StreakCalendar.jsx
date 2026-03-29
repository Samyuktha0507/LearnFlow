import React, { useMemo } from 'react';
import styles from './StreakCalendar.module.css';

export default function StreakCalendar({ days }) {
  const weeks = useMemo(() => {
    if (!days?.length) return [];
    const out = [];
    for (let i = 0; i < days.length; i += 7) {
      out.push(days.slice(i, i + 7));
    }
    return out.slice(-12);
  }, [days]);

  if (!weeks.length) return null;

  return (
    <div className={styles.wrap}>
      <h3 className={styles.title}>Activity</h3>
      <p className={styles.hint}>Each square is a day — green means you finished a lesson.</p>
      <div className={styles.scroll}>
        {weeks.map((week, wi) => (
          <div key={wi} className={styles.week}>
            {week.map((d) => (
              <div
                key={d.date}
                className={`${styles.cell} ${d.done ? styles.done : ''}`}
                title={`${d.date}${d.done ? ' — lesson done' : ''}`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
