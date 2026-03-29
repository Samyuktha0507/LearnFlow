from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from models import Base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./learning.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _sqlite_column_names(table: str) -> set:
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {r[1] for r in rows}
    except Exception:
        return set()


def _migrate_sqlite():
    if "sqlite" not in DATABASE_URL:
        return
    insp = inspect(engine)
    if not insp.has_table("student_profiles"):
        return
    cols = _sqlite_column_names("student_profiles")
    alters = []
    if "nutrients" not in cols:
        alters.append("ALTER TABLE student_profiles ADD COLUMN nutrients INTEGER DEFAULT 0")
    if "plant_stage" not in cols:
        alters.append("ALTER TABLE student_profiles ADD COLUMN plant_stage INTEGER DEFAULT 0")
    if "active_plan_id" not in cols:
        alters.append("ALTER TABLE student_profiles ADD COLUMN active_plan_id VARCHAR")
    if "notifications_enabled" not in cols:
        alters.append("ALTER TABLE student_profiles ADD COLUMN notifications_enabled BOOLEAN DEFAULT 0")
    if "password_hash" not in cols:
        alters.append("ALTER TABLE student_profiles ADD COLUMN password_hash VARCHAR")
    with engine.connect() as conn:
        for sql in alters:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()
    if insp.has_table("study_plans"):
        cols = _sqlite_column_names("study_plans")
        if "title" not in cols:
            with engine.connect() as conn:
                try:
                    conn.execute(text("ALTER TABLE study_plans ADD COLUMN title VARCHAR"))
                    conn.commit()
                except Exception:
                    conn.rollback()
    if insp.has_table("daily_progress"):
        cols = _sqlite_column_names("daily_progress")
        with engine.connect() as conn:
            if "plan_id" not in cols:
                try:
                    conn.execute(text("ALTER TABLE daily_progress ADD COLUMN plan_id VARCHAR"))
                    conn.commit()
                except Exception:
                    conn.rollback()
            if "nutrients_earned" not in cols:
                try:
                    conn.execute(text("ALTER TABLE daily_progress ADD COLUMN nutrients_earned INTEGER DEFAULT 0"))
                    conn.commit()
                except Exception:
                    conn.rollback()


def _backfill_active_plans():
    if "sqlite" not in DATABASE_URL:
        return
    from models import StudentProfile, StudyPlan

    db = SessionLocal()
    try:
        for s in db.query(StudentProfile).filter(StudentProfile.active_plan_id.is_(None)).all():
            sp = (
                db.query(StudyPlan)
                .filter(StudyPlan.student_id == s.id)
                .order_by(StudyPlan.created_at.desc())
                .first()
            )
            if sp:
                s.active_plan_id = sp.id
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()
    _backfill_active_plans()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
