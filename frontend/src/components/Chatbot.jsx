import React, { useState } from 'react';
import api from '../api';
import { formatApiError } from '../utils/apiError';
import styles from './Chatbot.module.css';

export default function Chatbot({ studentId }) {
  const [input, setInput] = useState('');
  const [lines, setLines] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const send = async (e) => {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || loading) return;
    setInput('');
    setError('');
    setLines((prev) => [...prev, { role: 'user', text: msg }]);
    setLoading(true);
    try {
      const { data } = await api.post(`/api/student/${studentId}/chat`, { message: msg });
      setLines((prev) => [...prev, { role: 'assistant', text: data.reply }]);
    } catch (err) {
      setError(formatApiError(err));
      setLines((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrap}>
      <h2 className={styles.h2}>Learning assistant</h2>
      <p className={styles.lead}>Ask questions about your goal — answers stay in this session.</p>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.chat}>
        {lines.length === 0 && <p className={styles.placeholder}>Try: “How should I break down this week’s topic?”</p>}
        {lines.map((l, i) => (
          <div key={i} className={l.role === 'user' ? styles.user : styles.bot}>
            {l.text}
          </div>
        ))}
        {loading && <div className={styles.thinking}>Thinking…</div>}
      </div>
      <form className={styles.form} onSubmit={send}>
        <input
          className={styles.input}
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className={styles.send} disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
