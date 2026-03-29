# Student Learning Consistency Agent — LearnFlow AI

An AI-powered learning coach built with **Google Gemini + FastAPI + React**.

## Quick Start

### 1. Backend

```bash
cd backend

# Create virtualenv (optional)
python -m venv venv
venv\Scripts\activate   # Windows

# Install deps
pip install -r requirements.txt

# Set your API key
copy .env.example .env
# Edit .env and add: GEMINI_API_KEY=your-gemini-key

# Run the API
uvicorn main:app --reload --port 8000
```

API docs at → http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App at → http://localhost:5173

In development, the frontend calls the API at **http://127.0.0.1:8000** (see `frontend/src/api.js`). Keep the backend running on port **8000** while you use the UI.

### Login problems

- **“Cannot reach the API”** — Start the backend (`uvicorn` on `127.0.0.1:8000`). If you use another port, set `VITE_API_URL` in `frontend/.env.local` to that URL.
- **“This account has no password (old data)”** — Accounts created before password auth have no hash. Stop the server, delete `backend/learning.db`, restart, and **sign up** again with email + password.

---

## Architecture

```
BUILDATHON/
├── backend/
│   ├── main.py         – FastAPI routes
│   ├── auth_utils.py   – bcrypt passwords
│   ├── ai_engine.py    – Gemini calls
│   ├── models.py       – SQLAlchemy ORM
│   ├── database.py     – DB session
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx
        ├── api.js
        └── components/
            ├── Auth.jsx            – Login / sign up
            ├── TodayLesson.jsx     – Daily lesson + quiz
            └── Dashboard.jsx       – Stats, plan creation
```

## Key Features

| Feature | Endpoint |
|---------|----------|
| Sign up | `POST /api/auth/signup` |
| Log in | `POST /api/auth/login` |
| Create study plan | `POST /api/student/{id}/plans` |
| Get today's lesson + quiz | `GET /api/student/{id}/today` |
| Submit quiz & update streak | `POST /api/student/{id}/complete-lesson` |
| Full dashboard data | `GET /api/student/{id}/dashboard` |
| AI adaptive check | `POST /api/student/{id}/check-adaptation` |
| Progress history | `GET /api/student/{id}/history` |
