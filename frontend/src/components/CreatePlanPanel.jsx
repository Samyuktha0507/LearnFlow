import React, { useState } from 'react';
import api from '../api';
import { formatApiError } from '../utils/apiError';
import styles from './CreatePlanPanel.module.css';

export default function CreatePlanPanel({ studentId, hasPlans, onCreated }) {
  const [form, setForm] = useState({
    goal: '',
    weeks: 8,
    experience_level: 'beginner',
    hours_per_week: 5,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.post(`/api/student/${studentId}/plans`, {
        goal: form.goal.trim(),
        weeks: parseInt(form.weeks, 10),
        experience_level: form.experience_level,
        hours_per_week: parseFloat(form.hours_per_week),
      });
      setForm({ goal: '', weeks: 8, experience_level: 'beginner', hours_per_week: 5 });
      onCreated?.();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className={styles.section} aria-labelledby="create-plan-heading">
      <h2 id="create-plan-heading" className={styles.h2}>
        {hasPlans ? 'Add another study plan' : 'Create your first study plan'}
      </h2>
      <p className={styles.lead}>
        {hasPlans
          ? 'You can run several plans and switch the active one under Plans.'
          : 'Tell us what you want to learn — we’ll generate a structured weekly path.'}
      </p>
      {error && <p className={styles.error}>{error}</p>}
      <form className={styles.form} onSubmit={submit}>
        <label className={styles.label}>Learning goal</label>
        <input
          className={styles.input}
          placeholder="e.g. Spanish for travel"
          value={form.goal}
          onChange={(e) => setForm({ ...form, goal: e.target.value })}
          required
        />
        <div className={styles.row2}>
          <div>
            <label className={styles.label}>Weeks</label>
            <select
              className={styles.input}
              value={form.weeks}
              onChange={(e) => setForm({ ...form, weeks: e.target.value })}
            >
              {[4, 6, 8, 10, 12].map((w) => (
                <option key={w} value={w}>{w} weeks</option>
              ))}
            </select>
          </div>
          <div>
            <label className={styles.label}>Level</label>
            <select
              className={styles.input}
              value={form.experience_level}
              onChange={(e) => setForm({ ...form, experience_level: e.target.value })}
            >
              {['beginner', 'intermediate', 'advanced'].map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>
        </div>
        <div className={styles.sliderGroup}>
          <label className={styles.label}>
            Hours per week: <span className={styles.sliderVal}>{form.hours_per_week}h</span>
          </label>
          <input
            type="range"
            min={1}
            max={20}
            step={0.5}
            value={form.hours_per_week}
            onChange={(e) => setForm({ ...form, hours_per_week: parseFloat(e.target.value) })}
            className={styles.slider}
          />
        </div>
        <button type="submit" className={styles.btn} disabled={loading}>
          {loading ? 'Generating your plan…' : 'Generate study plan'}
        </button>
      </form>
    </section>
  );
}
