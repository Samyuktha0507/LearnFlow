import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { formatApiError } from '../utils/apiError';
import styles from './Flashcards.module.css';

export default function Flashcards({ studentId }) {
  const [decks, setDecks] = useState([]);
  const [deckId, setDeckId] = useState(null);
  const [deckName, setDeckName] = useState('');
  const [front, setFront] = useState('');
  const [back, setBack] = useState('');
  const [due, setDue] = useState([]);
  const [showBack, setShowBack] = useState(false);
  const [error, setError] = useState('');

  const loadDecks = useCallback(() => {
    api
      .get(`/api/student/${studentId}/decks`)
      .then((r) => setDecks(r.data))
      .catch((e) => setError(formatApiError(e)));
  }, [studentId]);

  const loadDue = useCallback(
    (id) => {
      if (!id) return;
      api
        .get(`/api/student/${studentId}/decks/${id}/due`)
        .then((r) => {
          setDue(r.data);
          setShowBack(false);
        })
        .catch((e) => setError(formatApiError(e)));
    },
    [studentId]
  );

  useEffect(() => {
    loadDecks();
  }, [loadDecks]);

  useEffect(() => {
    if (deckId) loadDue(deckId);
  }, [deckId, loadDue]);

  const createDeck = async (e) => {
    e.preventDefault();
    if (!deckName.trim()) return;
    try {
      const { data } = await api.post(`/api/student/${studentId}/decks`, { name: deckName.trim() });
      setDeckId(data.id);
      setDeckName('');
      loadDecks();
    } catch (e) {
      setError(formatApiError(e));
    }
  };

  const addCard = async (e) => {
    e.preventDefault();
    if (!deckId || !front.trim() || !back.trim()) return;
    try {
      await api.post(`/api/student/${studentId}/decks/${deckId}/cards`, { front, back });
      setFront('');
      setBack('');
      loadDue(deckId);
    } catch (e) {
      setError(formatApiError(e));
    }
  };

  const card = due[0];

  const review = async (correct) => {
    if (!card) return;
    try {
      await api.post(`/api/student/${studentId}/cards/${card.id}/review`, { correct });
      setShowBack(false);
      loadDue(deckId);
    } catch (e) {
      setError(formatApiError(e));
    }
  };

  return (
    <div className={styles.wrap}>
      <h2 className={styles.h2}>Flashcards (spaced repetition)</h2>
      {error && <p className={styles.error}>{error}</p>}

      <form className={styles.row} onSubmit={createDeck}>
        <input
          className={styles.input}
          placeholder="New deck name"
          value={deckName}
          onChange={(e) => setDeckName(e.target.value)}
        />
        <button type="submit" className={styles.btn}>Create deck</button>
      </form>

      <div className={styles.pick}>
        <label className={styles.label}>Active deck</label>
        <select className={styles.input} value={deckId || ''} onChange={(e) => setDeckId(e.target.value || null)}>
          <option value="">Select…</option>
          {decks.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>

      {deckId && (
        <form className={styles.form} onSubmit={addCard}>
          <h3 className={styles.h3}>Add card</h3>
          <textarea className={styles.ta} placeholder="Front" value={front} onChange={(e) => setFront(e.target.value)} rows={2} />
          <textarea className={styles.ta} placeholder="Back" value={back} onChange={(e) => setBack(e.target.value)} rows={2} />
          <button type="submit" className={styles.btnPrimary}>Save card</button>
        </form>
      )}

      {deckId && (
        <div className={styles.session}>
          <h3 className={styles.h3}>Review due ({due.length})</h3>
          {!card && <p className={styles.muted}>No cards due right now. Add cards above.</p>}
          {card && (
            <div className={styles.card}>
              <button type="button" className={styles.flip} onClick={() => setShowBack(!showBack)}>
                {showBack ? card.back : card.front}
              </button>
              <p className={styles.hint}>{showBack ? 'Answer' : 'Question — tap to flip'}</p>
              {showBack && (
                <div className={styles.actions}>
                  <button type="button" className={styles.hard} onClick={() => review(false)}>Again</button>
                  <button type="button" className={styles.good} onClick={() => review(true)}>Got it</button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
