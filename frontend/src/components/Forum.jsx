import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { formatApiError } from '../utils/apiError';
import styles from './Forum.module.css';

export default function Forum({ studentId, studentName }) {
  const [posts, setPosts] = useState([]);
  const [thread, setThread] = useState(null);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [reply, setReply] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(() => {
    api
      .get('/api/forum/posts')
      .then((r) => setPosts(r.data))
      .catch((e) => setError(formatApiError(e)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openThread = (id) => {
    api
      .get(`/api/forum/posts/${id}`)
      .then((r) => setThread(r.data))
      .catch((e) => setError(formatApiError(e)));
  };

  const submitPost = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/api/student/${studentId}/forum/posts`, { title: title.trim(), body: body.trim() });
      setTitle('');
      setBody('');
      load();
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  const submitReply = async (e) => {
    e.preventDefault();
    if (!thread || !reply.trim()) return;
    try {
      await api.post(`/api/student/${studentId}/forum/posts/${thread.id}/replies`, { body: reply.trim() });
      setReply('');
      openThread(thread.id);
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  return (
    <div className={styles.wrap}>
      <h2 className={styles.h2}>Community</h2>
      <p className={styles.lead}>Share progress and ask for advice — be kind.</p>
      {error && <p className={styles.error}>{error}</p>}

      {thread ? (
        <div className={styles.thread}>
          <button type="button" className={styles.back} onClick={() => setThread(null)}>← All posts</button>
          <h3 className={styles.ttitle}>{thread.title}</h3>
          <p className={styles.meta}>{thread.author_name} · {thread.created_at?.slice(0, 10)}</p>
          <div className={styles.tbody}>{thread.body}</div>
          <ul className={styles.replies}>
            {(thread.replies || []).map((r) => (
              <li key={r.id}>
                <strong>{r.author_name}</strong>
                <span className={styles.rdate}>{r.created_at?.slice(0, 16)}</span>
                <p>{r.body}</p>
              </li>
            ))}
          </ul>
          <form onSubmit={submitReply} className={styles.rform}>
            <textarea
              className={styles.ta}
              rows={3}
              placeholder="Write a reply…"
              value={reply}
              onChange={(e) => setReply(e.target.value)}
            />
            <button type="submit" className={styles.btn}>Reply</button>
          </form>
        </div>
      ) : (
        <>
          <form className={styles.form} onSubmit={submitPost}>
            <h3 className={styles.h3}>New post</h3>
            <input className={styles.input} placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
            <textarea className={styles.ta} placeholder="What’s on your mind?" value={body} onChange={(e) => setBody(e.target.value)} rows={4} required />
            <button type="submit" className={styles.btnPrimary}>Post</button>
          </form>
          <ul className={styles.list}>
            {posts.map((p) => (
              <li key={p.id}>
                <button type="button" className={styles.item} onClick={() => openThread(p.id)}>
                  <span className={styles.ptitle}>{p.title}</span>
                  <span className={styles.pmeta}>{p.author_name} · {p.reply_count} replies</span>
                  <span className={styles.prev}>{p.body_preview}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
