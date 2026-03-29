import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { formatApiError } from '../utils/apiError';
import styles from './Plans.module.css';

export default function Plans({ studentId, onPlanActivated }) {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ goal: '', weeks: 8, experience_level: 'beginner', hours_per_week: 5 });

  const load = useCallback(() => {
    setLoading(true);
    api
      .get(`/api/student/${studentId}/plans`)
      .then((r) => setPlans(r.data))
      .catch((e) => setError(formatApiError(e)))
      .finally(() => setLoading(false));
  }, [studentId]);

  useEffect(() => {
    load();
  }, [load]);

  const activate = async (planId) => {
    try {
      await api.post(`/api/student/${studentId}/plans/${planId}/activate`);
      await load();
      onPlanActivated?.();
    } catch (e) {
      setError(formatApiError(e));
    }
  };

  const createPlan = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    try {
      await api.post(`/api/student/${studentId}/plans`, {
        goal: form.goal,
        weeks: parseInt(form.weeks, 10),
        experience_level: form.experience_level,
        hours_per_week: parseFloat(form.hours_per_week),
      });
      setForm({ ...form, goal: '' });
      await load();
      onPlanActivated?.();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <div className={styles.muted}>Loading plans…</div>;

  return (
    <div className={styles.wrap}>
      <h2 className={styles.h2}>Your plans</h2>
      <p className={styles.lead}>Switch the active plan for today&apos;s lesson, or add another learning track.</p>

      {error && <p className={styles.error}>{error}</p>}

      <ul className={styles.list}>
        {plans.map((p) => (
          <li key={p.id} className={styles.row}>
            <div>
              <div className={styles.title}>{p.title}</div>
              <div className={styles.meta}>{p.total_weeks} weeks · {p.created_at?.slice(0, 10)}</div>
            </div>
            {p.is_active ? (
              <span className={styles.badge}>Active</span>
            ) : (
              <button type="button" className={styles.btn} onClick={() => activate(p.id)}>
                Set active
              </button>
            )}
          </li>
        ))}
      </ul>

      <form className={styles.form} onSubmit={createPlan}>
        <h3 className={styles.h3}>Create a new plan</h3>
        <label className={styles.label}>Goal</label>
        <input
          className={styles.input}
          value={form.goal}
          onChange={(e) => setForm({ ...form, goal: e.target.value })}
          placeholder="e.g. Linear algebra"
          required
        />
        <div className={styles.row2}>
          <div>
            <label className={styles.label}>Weeks</label>
            <select className={styles.input} value={form.weeks} onChange={(e) => setForm({ ...form, weeks: e.target.value })}>
              {[4, 6, 8, 10, 12].map((w) => (
                <option key={w} value={w}>{w}</option>
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
        <button className={styles.submit} type="submit" disabled={creating}>
          {creating ? 'Generating…' : 'Add plan'}
        </button>
      </form>
    </div>
  );
}
