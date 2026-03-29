import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import api from '../api';
import { formatApiError } from '../utils/apiError';
import GrowthTree from './GrowthTree';
import StreakCalendar from './StreakCalendar';
import CreatePlanPanel from './CreatePlanPanel';
import styles from './Dashboard.module.css';

export default function Dashboard({ studentId, onGoToLesson, onPlanCreated }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboard = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.get(`/api/student/${studentId}/dashboard`),
      api.get(`/api/student/${studentId}/calendar?days=84`),
    ])
      .then(([d, c]) => {
        setData({ ...d.data, calendarDays: c.data.days });
        setLoading(false);
      })
      .catch((err) => {
        setError(formatApiError(err));
        setLoading(false);
      });
  }, [studentId]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  if (loading) return <LoadingDash />;
  if (error) {
    return (
      <div className={styles.wrap}>
        <div className={styles.errorBanner}>
          <p>{error}</p>
          <button type="button" className={styles.retryBtn} onClick={fetchDashboard}>Try again</button>
        </div>
      </div>
    );
  }
  if (!data) return <LoadingDash />;

  const {
    stats,
    quiz_trend,
    next_topics,
    badge,
    motivation,
    goal,
    plan_name,
    student_name,
    plant,
    calendarDays,
    plan_count = 0,
    has_active_plan: hasActivePlan = false,
  } = data;

  const displayGoal = goal === '—' ? 'Create a study plan below to set your focus.' : goal;
  const displayPlanLine = plan_name || (plan_count === 0 ? 'No study plan yet' : '');

  return (
    <div className={styles.wrap}>
      <div className={styles.banner}>
        <div className={styles.bannerLeft}>
          <div className={styles.avatar}>{student_name[0].toUpperCase()}</div>
          <div>
            <h2 className={styles.bannerName}>Hello, {student_name}</h2>
            <p className={styles.bannerGoal}>{displayGoal}</p>
            {displayPlanLine && <p className={styles.bannerPlan}>{displayPlanLine}</p>}
          </div>
        </div>
        {badge && <div className={styles.globalBadge}>{badge}</div>}
      </div>

      <CreatePlanPanel
        studentId={studentId}
        hasPlans={plan_count > 0}
        onCreated={() => {
          fetchDashboard();
          onPlanCreated?.();
        }}
      />

      <GrowthTree plant={plant} />
      <StreakCalendar days={calendarDays || []} />

      {motivation && (
        <div className={styles.motivationBox}>
          <span className={styles.motIcon} aria-hidden>—</span>
          <p className={styles.motText}>{motivation}</p>
        </div>
      )}

      <div className={styles.statsGrid}>
        <StatCard
          label="Current streak"
          value={`${stats.current_streak}`} unit="days"
          highlight={stats.current_streak >= 7}
        />
        <StatCard
          label="Longest streak"
          value={`${stats.longest_streak}`} unit="days"
        />
        <StatCard
          label="This week"
          value={`${stats.this_week_completion}%`}
          highlight={stats.this_week_completion >= 80}
        />
        <StatCard
          label="Avg quiz"
          value={`${stats.avg_quiz_score}%`}
          highlight={stats.avg_quiz_score >= 75}
        />
        <StatCard
          label="Nutrients"
          value={`${stats.nutrients ?? 0}`}
          highlight={(stats.nutrients ?? 0) >= 80}
        />
        <StatCard
          label="Lessons done"
          value={`${stats.total_lessons_completed}`} unit="total"
        />
      </div>


      {quiz_trend?.length > 0 && (
        <div className={styles.chartCard}>
          <h3 className={styles.cardTitle}>Quiz score trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={quiz_trend} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(90, 118, 128, 0.12)" />
              <XAxis dataKey="date" tick={{ fill: '#5c6e74', fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#5c6e74', fontSize: 11 }} unit="%" />
              <Tooltip
                contentStyle={{
                  background: '#ffffff',
                  border: '1px solid rgba(90, 118, 128, 0.2)',
                  borderRadius: 10,
                  boxShadow: '0 8px 24px rgba(44, 61, 66, 0.1)',
                }}
                labelStyle={{ color: '#2c3d42' }}
                itemStyle={{ color: '#5a8f8a' }}
                formatter={(v) => [`${v}%`, 'Score']}
              />
              <Line
                type="monotone" dataKey="score" stroke="url(#lineGrad)"
                strokeWidth={2.2} dot={{ fill: '#5a8f8a', r: 3.5 }}
                activeDot={{ r: 6, fill: '#6b7f9a' }}
              />
              <defs>
                <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#5a8f8a" />
                  <stop offset="100%" stopColor="#6b7f9a" />
                </linearGradient>
              </defs>
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {next_topics?.length > 0 && (
        <div className={styles.nextCard}>
          <h3 className={styles.cardTitle}>Coming up</h3>
          <div className={styles.nextList}>
            {next_topics.map((t, i) => (
              <div key={i} className={styles.nextItem}>
                <span className={styles.nextNum}>+{i + 1}</span>
                <span>{t}</span>
              </div>
            ))}
          </div>
        </div>
      )}


    </div>
  );
}

function StatCard({ label, value, unit, highlight }) {
  return (
    <div className={`${styles.statCard} ${highlight ? styles.statHighlight : ''}`}>
      <div className={styles.statVal}>
        {value}
        {unit && <span className={styles.statUnit}>{unit}</span>}
      </div>
      <div className={styles.statLabel}>{label}</div>
    </div>
  );
}

function LoadingDash() {
  return (
    <div className={styles.loadWrap}>
      {[100, 60, 80, 100, 60].map((w, i) => (
        <div key={i} className={styles.pulseBar} style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}
