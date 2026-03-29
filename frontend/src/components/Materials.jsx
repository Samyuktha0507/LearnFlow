import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { formatApiError } from '../utils/apiError';
import styles from './Materials.module.css';

export default function Materials({ studentId }) {
  const [items, setItems] = useState([]);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(() => {
    api
      .get(`/api/student/${studentId}/materials`)
      .then((r) => setItems(r.data))
      .catch((e) => setError(formatApiError(e)));
  }, [studentId]);

  useEffect(() => {
    load();
  }, [load]);

  const saveNote = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      await api.post(`/api/student/${studentId}/materials`, {
        title: title.trim(),
        kind: linkUrl.trim() ? 'link' : 'note',
        body: body.trim() || null,
        link_url: linkUrl.trim() || null,
      });
      setTitle('');
      setBody('');
      setLinkUrl('');
      load();
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    fd.append('title', file.name);
    try {
      await api.post(`/api/student/${studentId}/materials/upload`, fd);
      load();
    } catch (err) {
      setError(formatApiError(err));
    }
    e.target.value = '';
  };

  const remove = async (id) => {
    try {
      await api.delete(`/api/student/${studentId}/materials/${id}`);
      load();
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  return (
    <div className={styles.wrap}>
      <h2 className={styles.h2}>Materials</h2>
      <p className={styles.lead}>Notes, links, and files for your learning — stored with your account.</p>
      {error && <p className={styles.error}>{error}</p>}

      <form className={styles.form} onSubmit={saveNote}>
        <input className={styles.input} placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <textarea className={styles.ta} placeholder="Notes (optional)" value={body} onChange={(e) => setBody(e.target.value)} rows={3} />
        <input className={styles.input} placeholder="Link URL (optional)" value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} />
        <button type="submit" className={styles.btn}>Save</button>
      </form>

      <div className={styles.upload}>
        <label className={styles.fileLabel}>
          Upload file
          <input type="file" className={styles.file} onChange={upload} />
        </label>
      </div>

      <ul className={styles.list}>
        {items.map((m) => (
          <li key={m.id} className={styles.row}>
            <div>
              <div className={styles.mtitle}>{m.title}</div>
              <div className={styles.mkind}>{m.kind}</div>
              {m.body && <p className={styles.mbody}>{m.body}</p>}
              {m.link_url && (
                <a href={m.link_url} target="_blank" rel="noreferrer" className={styles.link}>{m.link_url}</a>
              )}
              {m.file_url && (
                <a href={m.file_url} target="_blank" rel="noreferrer" className={styles.link}>Open file</a>
              )}
            </div>
            <button type="button" className={styles.del} onClick={() => remove(m.id)}>Remove</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
