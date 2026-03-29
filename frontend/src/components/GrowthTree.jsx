import React from 'react';
import styles from './GrowthTree.module.css';

const STAGES = [
  { label: 'Seed', desc: 'Plant your habit' },
  { label: 'Sapling', desc: 'First roots' },
  { label: 'Young tree', desc: 'Steady growth' },
  { label: 'Growing tree', desc: 'Strong routine' },
  { label: 'Mature tree', desc: 'Deep learning' },
];

export default function GrowthTree({ plant }) {
  if (!plant) return null;
  const { stage = 0, stage_name, nutrients = 0, percent_to_next = 0, next_threshold } = plant;
  const meta = STAGES[Math.min(stage, STAGES.length - 1)];

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <h3 className={styles.title}>Your learning tree</h3>
        <p className={styles.sub}>
          Quiz nutrients: <strong>{nutrients}</strong>
          {next_threshold != null && (
            <span className={styles.nextHint}> · Next stage near {next_threshold} nutrients</span>
          )}
        </p>
      </div>
      <div className={styles.visual}>
        <div className={`${styles.tree} ${styles[`stage${stage}`]}`} aria-hidden />
        <div className={styles.caption}>
          <span className={styles.stageName}>{stage_name || meta.label}</span>
          <span className={styles.stageDesc}>{meta.desc}</span>
        </div>
      </div>
      {stage < 4 && (
        <div className={styles.barOuter}>
          <div className={styles.barInner} style={{ width: `${percent_to_next}%` }} />
        </div>
      )}
    </div>
  );
}
