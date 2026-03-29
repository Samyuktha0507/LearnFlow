import React, { useState, useEffect } from 'react';
import api from '../api';
import styles from './TodayLesson.module.css';

export default function TodayLesson({ studentId, onComplete }) {
  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [phase, setPhase] = useState('lesson'); // lesson | quiz | result
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [timeStart] = useState(Date.now());

  useEffect(() => {
    api.get(`/api/student/${studentId}/today`)
      .then(r => { setLesson(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [studentId]);

  const selectAnswer = (qIdx, option) => {
    setAnswers(prev => ({ ...prev, [qIdx]: option }));
  };

  const submitQuiz = async () => {
    setSubmitting(true);
    const quiz = lesson.quiz || [];
    const quizAnswers = quiz.map((q, i) => ({
      question: q.question,
      selected: answers[i] || '',
      correct: answers[i] === q.answer,
    }));
    const timeSec = Math.round((Date.now() - timeStart) / 1000 / 60);

    try {
      const { data } = await api.post(`/api/student/${studentId}/complete-lesson`, {
        topic: lesson.topic,
        plan_week: lesson.week,
        plan_day: lesson.day,
        plan_id: lesson.plan_id,
        time_spent: Math.max(timeSec, 1),
        quiz_answers: quizAnswers,
      });
      setResult(data);
      setPhase('result');
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingPulse />;
  if (!lesson) {
    return (
      <div className={styles.container}>
        <p className={styles.error}>
          No lesson available yet. Go to <strong>Home</strong> and create a study plan first.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {phase === 'lesson' && (
        <LessonView lesson={lesson} onStartQuiz={() => setPhase('quiz')} />
      )}
      {phase === 'quiz' && (
        <QuizView
          quiz={lesson.quiz}
          answers={answers}
          onSelect={selectAnswer}
          onSubmit={submitQuiz}
          submitting={submitting}
        />
      )}
      {phase === 'result' && (
        <ResultView result={result} onDone={onComplete} />
      )}
    </div>
  );
}

function LessonView({ lesson, onStartQuiz }) {
  const icons = { video: 'Video', reading: 'Read', practice: 'Practice', quiz: 'Quiz', interactive: 'Lab' };

  return (
    <div className={styles.lessonCard}>
      <div className={styles.weekBadge}>Week {lesson.week} · Day {lesson.day}</div>
      <div className={styles.weekTheme}>{lesson.week_theme}</div>
      <h2 className={styles.topicTitle}>{lesson.topic}</h2>

      <p className={styles.description}>{lesson.description}</p>

      <div className={styles.meta}>
        <span className={styles.metaBadge}>{lesson.duration_minutes} min</span>
        {(lesson.resource_types || []).map(r => (
          <span key={r} className={styles.metaBadge}>{icons[r] || r} · {r}</span>
        ))}
      </div>

      {lesson.learning_objectives?.length > 0 && (
        <div className={styles.objectives}>
          <h4>Learning Objectives</h4>
          <ul>
            {lesson.learning_objectives.map((obj, i) => <li key={i}>{obj}</li>)}
          </ul>
        </div>
      )}

      {lesson.already_completed_today ? (
        <div className={styles.alreadyDone}>
          You&apos;ve already completed today&apos;s lesson. Come back tomorrow.
        </div>
      ) : (
        <button type="button" className={styles.actionBtn} onClick={onStartQuiz}>
          Continue to quiz
        </button>
      )}
    </div>
  );
}

function QuizView({ quiz = [], answers, onSelect, onSubmit, submitting }) {
  const allAnswered = quiz.every((_, i) => answers[i]);

  return (
    <div className={styles.quizCard}>
      <h2 className={styles.quizTitle}>Short quiz</h2>
      <p className={styles.quizSub}>Five questions to reinforce today&apos;s focus</p>

      {quiz.map((q, i) => (
        <div key={i} className={styles.question}>
          <p className={styles.qText}><span className={styles.qNum}>{i + 1}.</span> {q.question}</p>
          <div className={styles.options}>
            {(q.options || []).map((opt, j) => {
              const letter = ['A', 'B', 'C', 'D'][j];
              const selected = answers[i] === letter;
              return (
                <button
                  type="button"
                  key={j}
                  className={`${styles.option} ${selected ? styles.selected : ''}`}
                  onClick={() => onSelect(i, letter)}
                >
                  <span className={styles.optLetter}>{letter}</span>
                  <span>{opt.replace(/^[A-D]\.\s*/, '')}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}

      <button
        type="button"
        className={styles.submitBtn}
        onClick={onSubmit}
        disabled={!allAnswered || submitting}
      >
        {submitting ? <><span className={styles.spinner} /> Submitting…</> : 'Submit answers'}
      </button>
    </div>
  );
}

function ResultView({ result, onDone }) {
  const score = result.quiz_score;
  const color = score >= 80 ? '#5a9a7a' : score >= 60 ? '#c9a227' : '#c45c5c';
  return (
    <div className={styles.resultCard}>
      <div className={styles.scoreRing} style={{ '--score-color': color }}>
        <div className={styles.scoreInner}>
          <span className={styles.scoreNum}>{score}%</span>
          <span className={styles.scoreLabel}>Score</span>
        </div>
      </div>

      {result.nutrients_earned != null && (
        <p className={styles.nutrients}>
          +{result.nutrients_earned} nutrients for your tree
          {result.plant?.stage_name ? ` · ${result.plant.stage_name}` : ''}
        </p>
      )}

      <h2 className={styles.resultMsg}>{result.message}</h2>

      {result.badge && (
        <div className={styles.badge}>{result.badge}</div>
      )}

      <div className={styles.streakRow}>
        <div className={styles.streakBox}>
          <span className={styles.streakCount}>{result.streak}-day streak</span>
        </div>
      </div>

      {result.needs_review && (
        <div className={styles.reviewWarning}>
          A review session may help reinforce this topic when you&apos;re ready.
        </div>
      )}

      <button type="button" className={styles.doneBtn} onClick={onDone}>
        Back to dashboard
      </button>
    </div>
  );
}

function LoadingPulse() {
  return (
    <div className={styles.loadingWrap}>
      <div className={styles.pulseBar} />
      <div className={styles.pulseBar} style={{ width: '60%' }} />
      <div className={styles.pulseBar} style={{ width: '80%' }} />
    </div>
  );
}
