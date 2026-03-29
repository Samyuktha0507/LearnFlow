from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import json
import os
import shutil
import uuid

from database import get_db, init_db
from models import (
    StudentProfile,
    StudyPlan,
    DailyProgress,
    AdaptiveAdjustment,
    ReminderLog,
    FlashcardDeck,
    FlashCard,
    ForumPost,
    ForumReply,
    ChatMessage,
    Material,
)
from ai_engine import (
    generate_study_plan,
    generate_quiz_for_topic,
    generate_motivation_message,
    generate_intervention,
    generate_chat_reply,
)
from auth_utils import hash_password, verify_password

app = FastAPI(title="LearnFlow API", version="2.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def on_startup():
    init_db()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class OnboardRequest(BaseModel):
    name: str
    email: str
    goal: str
    hours_per_week: float = 5.0
    experience_level: str = "beginner"
    timezone: str = "UTC"
    weeks: int = 8


class CompleteLessonRequest(BaseModel):
    topic: str
    plan_week: int
    plan_day: int
    time_spent: int
    quiz_answers: list
    notes: Optional[str] = ""
    plan_id: Optional[str] = None


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


class CreatePlanRequest(BaseModel):
    goal: str
    hours_per_week: float = 5.0
    experience_level: str = "beginner"
    weeks: int = 8


class DeckCreate(BaseModel):
    name: str


class CardCreate(BaseModel):
    front: str
    back: str


class ReviewCard(BaseModel):
    correct: bool


class ForumPostCreate(BaseModel):
    title: str
    body: str


class ForumReplyCreate(BaseModel):
    body: str


class ChatBody(BaseModel):
    message: str


class MaterialCreate(BaseModel):
    title: str
    kind: str = "note"
    body: Optional[str] = None
    link_url: Optional[str] = None
    plan_id: Optional[str] = None


class NotificationsBody(BaseModel):
    enabled: bool


# ─── Plant / nutrients ─────────────────────────────────────────────────────────

STAGE_NAMES = ["Seed", "Sapling", "Young tree", "Growing tree", "Mature tree"]
NUTRIENT_THRESHOLDS = [0, 80, 250, 550, 1000]


def plant_stage_from_nutrients(n: int) -> int:
    if n >= NUTRIENT_THRESHOLDS[4]:
        return 4
    if n >= NUTRIENT_THRESHOLDS[3]:
        return 3
    if n >= NUTRIENT_THRESHOLDS[2]:
        return 2
    if n >= NUTRIENT_THRESHOLDS[1]:
        return 1
    return 0


def plant_payload(nutrients: int) -> dict:
    stage = plant_stage_from_nutrients(nutrients)
    if stage >= 4:
        return {
            "nutrients": nutrients,
            "stage": stage,
            "stage_name": STAGE_NAMES[stage],
            "percent_to_next": 100,
            "next_threshold": None,
        }
    lo = NUTRIENT_THRESHOLDS[stage]
    hi = NUTRIENT_THRESHOLDS[stage + 1]
    pct = int(100 * (nutrients - lo) / max(hi - lo, 1))
    return {
        "nutrients": nutrients,
        "stage": stage,
        "stage_name": STAGE_NAMES[stage],
        "percent_to_next": min(100, max(0, pct)),
        "next_threshold": hi,
    }


def nutrients_from_quiz_score(score: float) -> int:
    return int(10 + round(score * 28))


def get_student_or_404(student_id: str, db: Session) -> StudentProfile:
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def get_active_plan(student: StudentProfile, db: Session) -> Optional[StudyPlan]:
    sp = None
    if student.active_plan_id:
        sp = db.query(StudyPlan).filter(StudyPlan.id == student.active_plan_id).first()
    if not sp:
        sp = (
            db.query(StudyPlan)
            .filter(StudyPlan.student_id == student.id)
            .order_by(StudyPlan.created_at.desc())
            .first()
        )
    return sp


def compute_current_day(anchor: datetime, plan: dict) -> tuple[int, int]:
    days_active = (datetime.utcnow() - anchor).days
    days_active = max(0, days_active)
    total_weeks = plan.get("total_weeks", 8)
    week_idx = min(days_active // 5, total_weeks - 1)
    weeks = plan.get("weeks") or []
    if not weeks:
        return 0, 0
    week_idx = min(week_idx, len(weeks) - 1)
    topics = weeks[week_idx].get("topics") or []
    if not topics:
        return week_idx, 0
    day_idx = min(days_active % 5, len(topics) - 1)
    return week_idx, day_idx


def get_achievement_badge(streak: int) -> Optional[str]:
    if streak >= 30:
        return "Learning legend"
    if streak >= 21:
        return "Monthly champion"
    if streak >= 14:
        return "Two-week warrior"
    if streak >= 7:
        return "Week of focus"
    if streak >= 3:
        return "Getting started"
    return None


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.post("/api/auth/signup")
def auth_signup(body: SignupRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.query(StudentProfile).filter(StudentProfile.email == email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    student = StudentProfile(
        name=body.name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        goal="—",
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return {"student_id": student.id, "name": student.name}


@app.post("/api/auth/login")
def auth_login(body: LoginBody, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    s = db.query(StudentProfile).filter(StudentProfile.email == email).first()
    if not s:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not s.password_hash:
        raise HTTPException(
            status_code=401,
            detail=(
                "This account has no password (old data). Delete backend/learning.db and sign up again, "
                "or use a new email."
            ),
        )
    if not verify_password(body.password, s.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    s.last_active = datetime.utcnow()
    db.commit()
    return {"student_id": s.id, "name": s.name}


# ─── Onboard (creates or updates user + new plan) ───────────────────────────

@app.post("/api/onboard")
def onboard_student(body: OnboardRequest, db: Session = Depends(get_db)):
    """Legacy: add a plan for an existing account (use POST /api/student/{id}/plans from the app)."""
    email = body.email.strip().lower()
    plan_dict = generate_study_plan(body.goal, body.hours_per_week, body.experience_level, body.weeks)

    student = db.query(StudentProfile).filter(StudentProfile.email == email).first()
    if not student:
        raise HTTPException(status_code=400, detail="Sign up first, then create a plan from your dashboard.")

    student.name = body.name
    student.goal = body.goal
    student.hours_per_week = body.hours_per_week
    student.experience_level = body.experience_level
    student.timezone = body.timezone
    student.last_active = datetime.utcnow()

    db.query(StudyPlan).filter(StudyPlan.student_id == student.id).update({StudyPlan.is_active: False})

    title = plan_dict.get("plan_name", "My plan")
    study_plan = StudyPlan(
        student_id=student.id,
        title=title,
        plan_data=json.dumps(plan_dict),
        total_weeks=body.weeks,
        start_date=datetime.utcnow(),
        is_active=True,
    )
    db.add(study_plan)
    db.flush()
    student.active_plan_id = study_plan.id
    db.commit()
    db.refresh(student)

    return {
        "student_id": student.id,
        "plan_id": study_plan.id,
        "plan": plan_dict,
        "message": f"Welcome, {body.name}. Your {body.weeks}-week plan is ready.",
    }


@app.get("/api/student/{student_id}/plans")
def list_plans(student_id: str, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    rows = db.query(StudyPlan).filter(StudyPlan.student_id == student_id).order_by(StudyPlan.created_at.desc()).all()
    out = []
    stu = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    active_id = stu.active_plan_id if stu else None
    for r in rows:
        try:
            pdata = json.loads(r.plan_data)
            pname = r.title or pdata.get("plan_name", "Plan")
        except Exception:
            pname = r.title or "Plan"
        out.append(
            {
                "id": r.id,
                "title": pname,
                "total_weeks": r.total_weeks,
                "is_active": r.id == active_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return out


@app.post("/api/student/{student_id}/plans")
def create_plan(student_id: str, body: CreatePlanRequest, db: Session = Depends(get_db)):
    student = get_student_or_404(student_id, db)
    plan_dict = generate_study_plan(body.goal, body.hours_per_week, body.experience_level, body.weeks)
    db.query(StudyPlan).filter(StudyPlan.student_id == student_id).update({StudyPlan.is_active: False})
    title = plan_dict.get("plan_name", "My plan")
    sp = StudyPlan(
        student_id=student_id,
        title=title,
        plan_data=json.dumps(plan_dict),
        total_weeks=body.weeks,
        start_date=datetime.utcnow(),
        is_active=True,
    )
    db.add(sp)
    db.flush()
    student.active_plan_id = sp.id
    student.goal = body.goal
    db.commit()
    return {"plan_id": sp.id, "plan": plan_dict}


@app.post("/api/student/{student_id}/plans/{plan_id}/activate")
def activate_plan(student_id: str, plan_id: str, db: Session = Depends(get_db)):
    student = get_student_or_404(student_id, db)
    sp = db.query(StudyPlan).filter(StudyPlan.id == plan_id, StudyPlan.student_id == student_id).first()
    if not sp:
        raise HTTPException(status_code=404, detail="Plan not found")
    db.query(StudyPlan).filter(StudyPlan.student_id == student_id).update({StudyPlan.is_active: False})
    sp.is_active = True
    student.active_plan_id = sp.id
    pdata = json.loads(sp.plan_data)
    student.goal = pdata.get("description", student.goal)
    db.commit()
    return {"ok": True, "active_plan_id": plan_id}


# ─── Today / lesson ───────────────────────────────────────────────────────────

@app.get("/api/student/{student_id}/today")
def get_today_lesson(student_id: str, plan_id: Optional[str] = None, db: Session = Depends(get_db)):
    student = get_student_or_404(student_id, db)
    sp = None
    if plan_id:
        sp = db.query(StudyPlan).filter(StudyPlan.id == plan_id, StudyPlan.student_id == student_id).first()
    if not sp:
        sp = get_active_plan(student, db)
    if not sp:
        raise HTTPException(status_code=404, detail="No study plan found. Create a plan first.")

    plan = json.loads(sp.plan_data)
    anchor = sp.start_date or sp.created_at or datetime.utcnow()
    w_idx, d_idx = compute_current_day(anchor, plan)

    weeks = plan.get("weeks") or []
    if not weeks or w_idx >= len(weeks):
        raise HTTPException(status_code=400, detail="Invalid plan data")
    week = weeks[w_idx]
    topics = week.get("topics") or []
    if not topics or d_idx >= len(topics):
        raise HTTPException(status_code=400, detail="No topic for this day")

    topic = topics[d_idx]

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    already_done = (
        db.query(DailyProgress)
        .filter(
            DailyProgress.student_id == student_id,
            DailyProgress.plan_id == sp.id,
            DailyProgress.date >= today_start,
            DailyProgress.status == "completed",
        )
        .first()
    )

    quiz = topic.get("quiz_questions") or generate_quiz_for_topic(topic["topic_name"], topic.get("description", ""))

    return {
        "plan_id": sp.id,
        "week": w_idx + 1,
        "day": d_idx + 1,
        "total_weeks": plan.get("total_weeks", sp.total_weeks),
        "topic": topic["topic_name"],
        "description": topic.get("description", ""),
        "duration_minutes": topic.get("duration_minutes", 45),
        "resource_types": topic.get("resource_types", []),
        "expected_outcome": topic.get("expected_outcome", ""),
        "quiz": quiz,
        "already_completed_today": bool(already_done),
        "week_theme": week.get("theme", ""),
        "learning_objectives": week.get("learning_objectives", []),
    }


@app.post("/api/student/{student_id}/complete-lesson")
def complete_lesson(student_id: str, body: CompleteLessonRequest, db: Session = Depends(get_db)):
    student = get_student_or_404(student_id, db)
    sp = None
    if body.plan_id:
        sp = db.query(StudyPlan).filter(StudyPlan.id == body.plan_id, StudyPlan.student_id == student_id).first()
    if not sp:
        sp = get_active_plan(student, db)
    if not sp:
        raise HTTPException(status_code=404, detail="No study plan found")

    correct = sum(1 for q in body.quiz_answers if q.get("correct"))
    score = correct / max(len(body.quiz_answers), 1)

    yesterday_start = (datetime.utcnow() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_done = (
        db.query(DailyProgress)
        .filter(
            DailyProgress.student_id == student_id,
            DailyProgress.date >= yesterday_start,
            DailyProgress.date < today_start,
            DailyProgress.status == "completed",
        )
        .first()
    )

    if yesterday_done:
        student.current_streak += 1
    else:
        student.current_streak = 1

    student.longest_streak = max(student.longest_streak, student.current_streak)
    student.total_lessons_completed += 1
    student.last_active = datetime.utcnow()

    n_pts = nutrients_from_quiz_score(score)
    student.nutrients = (student.nutrients or 0) + n_pts
    student.plant_stage = plant_stage_from_nutrients(student.nutrients)

    progress = DailyProgress(
        student_id=student_id,
        plan_id=sp.id,
        date=datetime.utcnow(),
        topic=body.topic,
        plan_week=body.plan_week,
        plan_day=body.plan_day,
        status="completed",
        duration_actual=body.time_spent,
        quiz_score=score,
        quiz_answers=json.dumps(body.quiz_answers),
        notes=body.notes,
        nutrients_earned=n_pts,
    )
    db.add(progress)
    db.commit()

    badge = get_achievement_badge(student.current_streak)
    needs_review = score < 0.7

    return {
        "success": True,
        "quiz_score": round(score * 100),
        "nutrients_earned": n_pts,
        "plant": plant_payload(student.nutrients),
        "correct": correct,
        "total": len(body.quiz_answers),
        "streak": student.current_streak,
        "badge": badge,
        "needs_review": needs_review,
        "message": (
            f"Score {round(score * 100)}%. Consider a short review when you can."
            if needs_review
            else f"Score {round(score * 100)}%. +{n_pts} nutrients for your tree. Streak: {student.current_streak} days."
        ),
    }


# ─── Dashboard & calendar ─────────────────────────────────────────────────────

@app.get("/api/student/{student_id}/calendar")
def get_calendar(student_id: str, days: int = 84, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    days = min(max(days, 7), 400)
    end = datetime.utcnow().date()
    start = end - timedelta(days=days - 1)

    rows = (
        db.query(DailyProgress)
        .filter(
            DailyProgress.student_id == student_id,
            DailyProgress.status == "completed",
            DailyProgress.date >= datetime.combine(start, datetime.min.time()),
        )
        .all()
    )
    done_days = set()
    for r in rows:
        done_days.add(r.date.date().isoformat())

    out = []
    d = start
    while d <= end:
        ds = d.isoformat()
        out.append({"date": ds, "done": ds in done_days})
        d += timedelta(days=1)
    return {"days": out}


@app.get("/api/student/{student_id}/dashboard")
def get_dashboard(student_id: str, db: Session = Depends(get_db)):
    student = get_student_or_404(student_id, db)
    sp = get_active_plan(student, db)
    plan = json.loads(sp.plan_data) if sp else {}

    week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    this_week = (
        db.query(DailyProgress)
        .filter(DailyProgress.student_id == student_id, DailyProgress.date >= week_start)
        .all()
    )
    completed_this_week = sum(1 for p in this_week if p.status == "completed")
    week_completion = min(round((completed_this_week / 5) * 100), 100)

    recent = (
        db.query(DailyProgress)
        .filter(DailyProgress.student_id == student_id, DailyProgress.quiz_score.isnot(None))
        .order_by(DailyProgress.date.desc())
        .limit(10)
        .all()
    )

    avg_quiz = round(sum(p.quiz_score for p in recent) / max(len(recent), 1) * 100)

    next_topics = []
    if sp and plan and "weeks" in plan:
        anchor = sp.start_date or sp.created_at or datetime.utcnow()
        w_idx, d_idx = compute_current_day(anchor, plan)
        for i in range(1, 4):
            nd = d_idx + i
            nw = w_idx + nd // 5
            nd = nd % 5
            weeks = plan.get("weeks") or []
            if nw < len(weeks):
                tps = weeks[nw].get("topics") or []
                if nd < len(tps):
                    next_topics.append(tps[nd]["topic_name"])

    badge = get_achievement_badge(student.current_streak)
    if sp:
        wk = (datetime.utcnow() - (sp.start_date or sp.created_at or student.created_at)).days // 5 + 1
    else:
        wk = 1
    motivation = generate_motivation_message(
        student.name,
        student.current_streak,
        recent[0].topic if recent else "your next lesson",
        wk,
        plan.get("total_weeks", 8),
    )

    plan_count = db.query(StudyPlan).filter(StudyPlan.student_id == student_id).count()

    return {
        "student_name": student.name,
        "goal": student.goal,
        "plan_name": plan.get("plan_name", ""),
        "plan_count": plan_count,
        "has_active_plan": sp is not None,
        "active_plan_id": student.active_plan_id,
        "plant": plant_payload(student.nutrients or 0),
        "stats": {
            "current_streak": student.current_streak,
            "longest_streak": student.longest_streak,
            "total_lessons_completed": student.total_lessons_completed,
            "this_week_completion": week_completion,
            "avg_quiz_score": avg_quiz,
            "nutrients": student.nutrients or 0,
        },
        "badge": badge,
        "motivation": motivation,
        "quiz_trend": [
            {"date": p.date.strftime("%b %d"), "topic": p.topic, "score": round(p.quiz_score * 100)}
            for p in reversed(recent)
        ],
        "next_topics": next_topics,
        "notifications_enabled": bool(student.notifications_enabled),
    }


@app.post("/api/student/{student_id}/notifications")
def set_notifications(student_id: str, body: NotificationsBody, db: Session = Depends(get_db)):
    student = get_student_or_404(student_id, db)
    student.notifications_enabled = body.enabled
    db.commit()
    return {"notifications_enabled": body.enabled}


@app.post("/api/student/{student_id}/check-adaptation")
def check_adaptation(student_id: str, db: Session = Depends(get_db)):
    student = get_student_or_404(student_id, db)

    week_ago = datetime.utcnow() - timedelta(days=7)
    recent = (
        db.query(DailyProgress)
        .filter(DailyProgress.student_id == student_id, DailyProgress.date >= week_ago)
        .all()
    )

    if not recent:
        return {"status": "ok", "message": "Not enough data yet — keep going!"}

    scores = [p.quiz_score for p in recent if p.quiz_score is not None]
    avg_score = sum(scores) / max(len(scores), 1)
    completion_rate = sum(1 for p in recent if p.status == "completed") / 7

    needs_intervention = avg_score < 0.6 or completion_rate < 0.5

    if not needs_intervention:
        return {"status": "on_track", "avg_score": round(avg_score * 100), "completion": round(completion_rate * 100)}

    intervention = generate_intervention(student.name, student.goal, avg_score, completion_rate, student.current_streak)

    adj = AdaptiveAdjustment(
        student_id=student_id,
        reason=f"Quiz avg {round(avg_score*100)}%, completion {round(completion_rate*100)}%",
        adjustment_data=json.dumps(intervention),
    )
    db.add(adj)
    db.commit()

    return {
        "status": "intervention",
        "intervention": intervention,
        "avg_score": round(avg_score * 100),
        "completion": round(completion_rate * 100),
    }


@app.get("/api/student/{student_id}/history")
def get_history(student_id: str, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    history = (
        db.query(DailyProgress)
        .filter(DailyProgress.student_id == student_id)
        .order_by(DailyProgress.date.desc())
        .all()
    )

    return [
        {
            "date": p.date.strftime("%Y-%m-%d"),
            "topic": p.topic,
            "week": p.plan_week,
            "day": p.plan_day,
            "status": p.status,
            "duration_actual": p.duration_actual,
            "quiz_score": round(p.quiz_score * 100) if p.quiz_score is not None else None,
            "plan_id": p.plan_id,
        }
        for p in history
    ]


@app.get("/api/students")
def list_students(db: Session = Depends(get_db)):
    students = db.query(StudentProfile).order_by(StudentProfile.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "goal": s.goal,
            "streak": s.current_streak,
            "total_completed": s.total_lessons_completed,
            "last_active": s.last_active.strftime("%Y-%m-%d %H:%M") if s.last_active else None,
        }
        for s in students
    ]


# ─── Flashcards ───────────────────────────────────────────────────────────────

@app.get("/api/student/{student_id}/decks")
def list_decks(student_id: str, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    decks = db.query(FlashcardDeck).filter(FlashcardDeck.student_id == student_id).all()
    return [{"id": d.id, "name": d.name, "created_at": d.created_at.isoformat()} for d in decks]


@app.post("/api/student/{student_id}/decks")
def create_deck(student_id: str, body: DeckCreate, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    d = FlashcardDeck(student_id=student_id, name=body.name.strip())
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "name": d.name}


@app.post("/api/student/{student_id}/decks/{deck_id}/cards")
def add_card(student_id: str, deck_id: str, body: CardCreate, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id, FlashcardDeck.student_id == student_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    c = FlashCard(deck_id=deck_id, front=body.front.strip(), back=body.back.strip())
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id}


@app.get("/api/student/{student_id}/decks/{deck_id}/due")
def due_cards(student_id: str, deck_id: str, limit: int = 20, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id, FlashcardDeck.student_id == student_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    now = datetime.utcnow()
    cards = (
        db.query(FlashCard)
        .filter(FlashCard.deck_id == deck_id, FlashCard.due_at <= now)
        .order_by(FlashCard.due_at.asc())
        .limit(limit)
        .all()
    )
    return [
        {"id": c.id, "front": c.front, "back": c.back, "due_at": c.due_at.isoformat() if c.due_at else None}
        for c in cards
    ]


@app.post("/api/student/{student_id}/cards/{card_id}/review")
def review_card(student_id: str, card_id: str, body: ReviewCard, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    c = db.query(FlashCard).filter(FlashCard.id == card_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Card not found")
    deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == c.deck_id).first()
    if not deck or deck.student_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    now = datetime.utcnow()
    if body.correct:
        c.repetitions = (c.repetitions or 0) + 1
        c.interval_days = max(1, int((c.interval_days or 1) * 1.6))
        c.ease = min(2.6, (c.ease or 2.5) + 0.05)
    else:
        c.repetitions = 0
        c.interval_days = 1
        c.ease = max(1.3, (c.ease or 2.5) - 0.2)

    c.last_reviewed_at = now
    c.due_at = now + timedelta(days=c.interval_days)
    db.commit()
    return {"ok": True, "next_due": c.due_at.isoformat()}


# ─── Forum ────────────────────────────────────────────────────────────────────

@app.get("/api/forum/posts")
def forum_list(db: Session = Depends(get_db)):
    posts = db.query(ForumPost).order_by(ForumPost.created_at.desc()).limit(80).all()
    out = []
    for p in posts:
        author = db.query(StudentProfile).filter(StudentProfile.id == p.author_id).first()
        rc = db.query(ForumReply).filter(ForumReply.post_id == p.id).count()
        out.append(
            {
                "id": p.id,
                "title": p.title,
                "body_preview": (p.body[:220] + "…") if len(p.body) > 220 else p.body,
                "author_name": author.name if author else "Learner",
                "created_at": p.created_at.isoformat() if p.created_at else "",
                "reply_count": rc,
            }
        )
    return out


@app.post("/api/student/{student_id}/forum/posts")
def forum_create(student_id: str, body: ForumPostCreate, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    p = ForumPost(author_id=student_id, title=body.title.strip(), body=body.body.strip())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id}


@app.get("/api/forum/posts/{post_id}")
def forum_get(post_id: str, db: Session = Depends(get_db)):
    p = db.query(ForumPost).filter(ForumPost.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    author = db.query(StudentProfile).filter(StudentProfile.id == p.author_id).first()
    replies = db.query(ForumReply).filter(ForumReply.post_id == post_id).order_by(ForumReply.created_at.asc()).all()
    rep_out = []
    for r in replies:
        ra = db.query(StudentProfile).filter(StudentProfile.id == r.author_id).first()
        rep_out.append(
            {
                "id": r.id,
                "body": r.body,
                "author_name": ra.name if ra else "Learner",
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
        )
    return {
        "id": p.id,
        "title": p.title,
        "body": p.body,
        "author_name": author.name if author else "Learner",
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "replies": rep_out,
    }


@app.post("/api/student/{student_id}/forum/posts/{post_id}/replies")
def forum_reply(student_id: str, post_id: str, body: ForumReplyCreate, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    p = db.query(ForumPost).filter(ForumPost.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    r = ForumReply(post_id=post_id, author_id=student_id, body=body.body.strip())
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id}


# ─── Chat ─────────────────────────────────────────────────────────────────────

@app.post("/api/student/{student_id}/chat")
def chat(student_id: str, body: ChatBody, db: Session = Depends(get_db)):
    student = get_student_or_404(student_id, db)
    msg = body.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message required")

    past = (
        db.query(ChatMessage)
        .filter(ChatMessage.student_id == student_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(12)
        .all()
    )
    past = list(reversed(past))
    history_text = "\n".join(f"{m.role}: {m.content}" for m in past[-8:])

    reply_text = generate_chat_reply(student.name, student.goal, msg, history_text)

    db.add(ChatMessage(student_id=student_id, role="user", content=msg))
    db.add(ChatMessage(student_id=student_id, role="assistant", content=reply_text))
    db.commit()

    return {"reply": reply_text}


# ─── Materials ────────────────────────────────────────────────────────────────

@app.get("/api/student/{student_id}/materials")
def materials_list(student_id: str, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    rows = db.query(Material).filter(Material.student_id == student_id).order_by(Material.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "kind": r.kind,
            "body": r.body,
            "link_url": r.link_url,
            "file_url": f"/uploads/{os.path.basename(r.file_path)}" if r.file_path else None,
            "plan_id": r.plan_id,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]


@app.post("/api/student/{student_id}/materials")
def materials_create(student_id: str, body: MaterialCreate, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    m = Material(
        student_id=student_id,
        plan_id=body.plan_id,
        title=body.title.strip(),
        kind=body.kind,
        body=body.body,
        link_url=body.link_url,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id}


@app.post("/api/student/{student_id}/materials/upload")
async def materials_upload(
    student_id: str,
    db: Session = Depends(get_db),
    title: str = Form("File"),
    plan_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    get_student_or_404(student_id, db)
    sid_dir = os.path.join(UPLOAD_DIR, student_id)
    os.makedirs(sid_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1][:12]
    fn = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(sid_dir, fn)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    rel = os.path.join(student_id, fn).replace("\\", "/")
    m = Material(
        student_id=student_id,
        plan_id=plan_id,
        title=title or (file.filename or "Upload"),
        kind="file",
        file_path=rel,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id, "file_url": f"/uploads/{rel}"}


@app.delete("/api/student/{student_id}/materials/{material_id}")
def materials_delete(student_id: str, material_id: str, db: Session = Depends(get_db)):
    get_student_or_404(student_id, db)
    m = db.query(Material).filter(Material.id == material_id, Material.student_id == student_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Not found")
    if m.file_path:
        fp = os.path.join(UPLOAD_DIR, m.file_path)
        if os.path.isfile(fp):
            try:
                os.remove(fp)
            except OSError:
                pass
    db.delete(m)
    db.commit()
    return {"ok": True}


@app.get("/")
def root():
    return {"message": "LearnFlow API", "version": "2.0.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
