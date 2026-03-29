import React, { useState, useEffect } from 'react';
import './index.css';
import Auth from './components/Auth';
import Dashboard from './components/Dashboard';
import TodayLesson from './components/TodayLesson';
import Plans from './components/Plans';
import Flashcards from './components/Flashcards';
import Forum from './components/Forum';
import Chatbot from './components/Chatbot';
import Materials from './components/Materials';
import api from './api';
import { useDailyReminder } from './hooks/useDailyReminder';
import appStyles from './App.module.css';

const NAV = [
  { id: 'dashboard', label: 'Home' },
  { id: 'lesson', label: 'Lesson' },
  { id: 'plans', label: 'Plans' },
  { id: 'flashcards', label: 'Cards' },
  { id: 'forum', label: 'Forum' },
  { id: 'chat', label: 'Assistant' },
  { id: 'materials', label: 'Materials' },
];

export default function App() {
  const [studentId, setStudentId] = useState(() => localStorage.getItem('student_id'));
  const [activeTab, setActiveTab] = useState('dashboard');
  const [notifEnabled, setNotifEnabled] = useState(false);
  const [dashKey, setDashKey] = useState(0);

  useEffect(() => {
    if (!studentId) return;
    console.log("studentId changed in App, fetching dashboard for:", studentId);
    api
      .get(`/api/student/${studentId}/dashboard`)
      .then((r) => {
        console.log("Dashboard data received:", r.data);
        setNotifEnabled(!!r.data.notifications_enabled);
      })
      .catch((err) => {
        console.error("Error fetching dashboard:", err);
      });
  }, [studentId, dashKey]);

  useDailyReminder(studentId, notifEnabled);

  const handleAuthenticated = (id) => {
    console.log("handleAuthenticated called with ID:", id);
    if (!id) {
      console.error("Invalid student ID:", id);
      return;
    }
    console.log("Setting studentId state to:", id);
    setStudentId(id);
    localStorage.setItem('student_id', id);
    console.log("localStorage updated with student_id:", id);
    setActiveTab('dashboard');
    setDashKey((k) => k + 1);
  };

  const handleLogout = () => {
    localStorage.removeItem('student_id');
    setStudentId(null);
  };

  const toggleNotifications = async () => {
    if (!studentId) return;
    const next = !notifEnabled;
    if (next && 'Notification' in window && Notification.permission === 'default') {
      await Notification.requestPermission();
    }
    try {
      await api.post(`/api/student/${studentId}/notifications`, { enabled: next });
      setNotifEnabled(next);
    } catch {
      setNotifEnabled(next);
    }
  };

  const onPlanActivated = () => setDashKey((k) => k + 1);

  if (!studentId) {
    console.log("No studentId, rendering Auth component");
    return <Auth onAuthenticated={handleAuthenticated} />;
  }

  console.log("StudentId exists:", studentId, "rendering Dashboard");


  return (
    <div className={appStyles.app}>
      <div className={appStyles.orb1} />
      <div className={appStyles.orb2} />

      <nav className={appStyles.nav}>
        <div className={appStyles.navBrand}>
          <span className={appStyles.brandIcon} aria-hidden />
          <span className={appStyles.brandName}>LearnFlow</span>
        </div>

        <div className={appStyles.tabs}>
          {NAV.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              className={`${appStyles.tab} ${activeTab === id ? appStyles.tabActive : ''}`}
              onClick={() => setActiveTab(id)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className={appStyles.navRight}>
          <button
            type="button"
            className={`${appStyles.bell} ${notifEnabled ? appStyles.bellOn : ''}`}
            onClick={toggleNotifications}
            title={notifEnabled ? 'Daily reminders on (9:00)' : 'Enable daily reminders'}
          >
            {notifEnabled ? '🔔' : '🔕'}
          </button>
          <button type="button" className={appStyles.logoutBtn} onClick={handleLogout} title="Sign out">
            Logout
          </button>
        </div>
      </nav>

      <main className={appStyles.main}>
        {activeTab === 'dashboard' && (
          <Dashboard
            key={dashKey}
            studentId={studentId}
            onGoToLesson={() => setActiveTab('lesson')}
            onPlanCreated={() => setDashKey((k) => k + 1)}
          />
        )}
        {activeTab === 'lesson' && (
          <TodayLesson
            studentId={studentId}
            onComplete={() => {
              setActiveTab('dashboard');
              setDashKey((k) => k + 1);
            }}
          />
        )}
        {activeTab === 'plans' && <Plans studentId={studentId} onPlanActivated={onPlanActivated} />}
        {activeTab === 'flashcards' && <Flashcards studentId={studentId} />}
        {activeTab === 'forum' && <Forum studentId={studentId} />}
        {activeTab === 'chat' && <Chatbot studentId={studentId} />}
        {activeTab === 'materials' && <Materials studentId={studentId} />}
      </main>
    </div>
  );
}
