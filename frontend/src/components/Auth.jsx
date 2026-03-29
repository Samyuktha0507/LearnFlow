import React, { useState } from 'react';
import api from '../api';
import { formatApiError } from '../utils/apiError';
import styles from './Auth.module.css';

export default function Auth({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAuthSuccess = (studentId) => {
    console.log("Authentication successful! Student ID:", studentId);
    
    // 1. Save to localStorage
    localStorage.setItem('student_id', studentId);
    
    // 2. Notify the parent App component (this triggers the state change to show Dashboard)
    if (onAuthenticated) {
      onAuthenticated(studentId);
    }

    // 3. Optional: Force a storage event in case App.js is listening for it
    window.dispatchEvent(new Event('storage'));
  };

  const submitLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/api/auth/login', {
        email: email.trim().toLowerCase(),
        password,
      });
      console.log("Login response:", response);
      console.log("Student ID from response:", response.data.student_id);
      if (response.data && response.data.student_id) {
        handleAuthSuccess(response.data.student_id);
      } else {
        console.error("No student_id in response:", response.data);
        setError("Authentication failed: No student ID received");
      }
    } catch (err) {
      console.error("Login Error:", err);
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const submitSignup = async (e) => {
    e.preventDefault();
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      console.log("Attempting signup for:", email);
      const response = await api.post('/api/auth/signup', {
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password,
      });
      console.log("Signup response:", response);
      console.log("Student ID from response:", response.data.student_id);
      if (response.data && response.data.student_id) {
        handleAuthSuccess(response.data.student_id);
      } else {
        console.error("No student_id in response:", response.data);
        setError("Account creation failed: No student ID received");
      }
    } catch (err) {
      console.error("Signup Error:", err);
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.blob1} />
      <div className={styles.blob2} />

      <div className={styles.card}>
        <div className={styles.brand}>
          <div className={styles.logo} aria-hidden />
          <div>
            <h1 className={styles.title}>LearnFlow</h1>
            <p className={styles.tagline}>Steady learning, one session at a time</p>
          </div>
        </div>

        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${mode === 'login' ? styles.tabActive : ''}`}
            onClick={() => { setMode('login'); setError(''); }}
          >
            Log in
          </button>
          <button
            type="button"
            className={`${styles.tab} ${mode === 'signup' ? styles.tabActive : ''}`}
            onClick={() => { setMode('signup'); setError(''); }}
          >
            Sign up
          </button>
        </div>

        {error && <p className={styles.error}>{error}</p>}

        {mode === 'login' ? (
          <form className={styles.form} onSubmit={submitLogin}>
            <label className={styles.label}>Email</label>
            <input
              className={styles.input}
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <label className={styles.label}>Password</label>
            <input
              className={styles.input}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button className={styles.submit} type="submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Continue'}
            </button>
          </form>
        ) : (
          <form className={styles.form} onSubmit={submitSignup}>
            <label className={styles.label}>Name</label>
            <input
              className={styles.input}
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <label className={styles.label}>Email</label>
            <input
              className={styles.input}
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <label className={styles.label}>Password (8+ characters)</label>
            <input
              className={styles.input}
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
            <button className={styles.submit} type="submit" disabled={loading}>
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </form>
        )}

        <p className={styles.hint}>
          After you sign in, you'll land on your dashboard and can create a study plan there.
        </p>
      </div>
    </div>
  );
}