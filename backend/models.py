from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=True)
    goal = Column(String, nullable=False)
    hours_per_week = Column(Float, default=5.0)
    experience_level = Column(String, default="beginner")
    timezone = Column(String, default="UTC")
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    total_lessons_completed = Column(Integer, default=0)
    nutrients = Column(Integer, default=0)
    plant_stage = Column(Integer, default=0)  # 0 seed … 4 tree
    active_plan_id = Column(String, nullable=True, index=True)
    notifications_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    study_plans = relationship("StudyPlan", back_populates="student", foreign_keys="StudyPlan.student_id")
    daily_progress = relationship("DailyProgress", back_populates="student")
    adaptations = relationship("AdaptiveAdjustment", back_populates="student")
    reminder_logs = relationship("ReminderLog", back_populates="student")
    flashcard_decks = relationship("FlashcardDeck", back_populates="student")
    forum_posts = relationship("ForumPost", back_populates="author")
    chat_messages = relationship("ChatMessage", back_populates="student")
    materials = relationship("Material", back_populates="student")


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profiles.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    plan_data = Column(Text, nullable=False)
    total_weeks = Column(Integer, default=8)
    start_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="study_plans", foreign_keys=[student_id])


class DailyProgress(Base):
    __tablename__ = "daily_progress"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profiles.id"), nullable=False, index=True)
    plan_id = Column(String, ForeignKey("study_plans.id"), nullable=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    topic = Column(String)
    plan_week = Column(Integer)
    plan_day = Column(Integer)
    status = Column(String, default="pending")
    duration_actual = Column(Integer, default=0)
    quiz_score = Column(Float, nullable=True)
    quiz_answers = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    nutrients_earned = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="daily_progress")


class AdaptiveAdjustment(Base):
    __tablename__ = "adaptive_adjustments"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profiles.id"), nullable=False)
    reason = Column(String)
    adjustment_data = Column(Text)
    applied_date = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="adaptations")


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profiles.id"), nullable=False)
    topic = Column(String)
    sent_at = Column(DateTime, default=datetime.utcnow)
    opened = Column(Boolean, default=False)

    student = relationship("StudentProfile", back_populates="reminder_logs")


class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profiles.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="flashcard_decks")
    cards = relationship("FlashCard", back_populates="deck", cascade="all, delete-orphan")


class FlashCard(Base):
    __tablename__ = "flash_cards"

    id = Column(String, primary_key=True, default=gen_uuid)
    deck_id = Column(String, ForeignKey("flashcard_decks.id"), nullable=False, index=True)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    interval_days = Column(Integer, default=1)
    ease = Column(Float, default=2.5)
    due_at = Column(DateTime, default=datetime.utcnow)
    last_reviewed_at = Column(DateTime, nullable=True)
    repetitions = Column(Integer, default=0)

    deck = relationship("FlashcardDeck", back_populates="cards")


class ForumPost(Base):
    __tablename__ = "forum_posts"

    id = Column(String, primary_key=True, default=gen_uuid)
    author_id = Column(String, ForeignKey("student_profiles.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    author = relationship("StudentProfile", back_populates="forum_posts")
    replies = relationship("ForumReply", back_populates="post", cascade="all, delete-orphan")


class ForumReply(Base):
    __tablename__ = "forum_replies"

    id = Column(String, primary_key=True, default=gen_uuid)
    post_id = Column(String, ForeignKey("forum_posts.id"), nullable=False, index=True)
    author_id = Column(String, ForeignKey("student_profiles.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("ForumPost", back_populates="replies")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profiles.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="chat_messages")


class Material(Base):
    __tablename__ = "materials"

    id = Column(String, primary_key=True, default=gen_uuid)
    student_id = Column(String, ForeignKey("student_profiles.id"), nullable=False, index=True)
    plan_id = Column(String, ForeignKey("study_plans.id"), nullable=True)
    title = Column(String, nullable=False)
    kind = Column(String, default="note")  # note | link | file
    body = Column(Text, nullable=True)
    link_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="materials")
