import google.generativeai as genai
import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Use a current model ID; override with GEMINI_MODEL if needed.
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_api_key = os.getenv("GEMINI_API_KEY")
if _api_key:
    genai.configure(api_key=_api_key)


def _fallback_topic(goal: str, week_num: int, day: int) -> dict:
    return {
        "day": day,
        "topic_name": f"Week {week_num} · Session {day}: {goal} — core concepts",
        "duration_minutes": 45,
        "description": (
            f"Review fundamentals for “{goal}”, take short notes, and do one hands-on exercise. "
            "Focus on clarity over speed."
        ),
        "resource_types": ["reading", "practice"],
        "quiz_questions": [
            {
                "question": "What is the best first step when learning a new skill?",
                "options": ["Skip basics and jump to advanced topics", "Build a small daily habit", "Only watch videos", "Avoid practice"],
                "answer": "B",
            },
            {
                "question": "Why is spaced repetition useful?",
                "options": ["It removes the need to study", "It strengthens memory over time", "It only works for languages", "It replaces sleep"],
                "answer": "B",
            },
            {
                "question": "What makes a good study session?",
                "options": ["Multitasking heavily", "A clear goal and focused time", "Studying only when tired", "Avoiding breaks entirely"],
                "answer": "B",
            },
            {
                "question": "How should you handle mistakes while learning?",
                "options": ["Ignore them", "Use them as feedback and adjust", "Quit the topic", "Copy answers without thinking"],
                "answer": "B",
            },
            {
                "question": "What helps consistency most?",
                "options": ["Rare long cram sessions", "Regular shorter sessions", "Waiting for motivation", "Avoiding a schedule"],
                "answer": "B",
            },
        ],
        "expected_outcome": "You can explain one core idea and complete one small practice task.",
    }


def build_fallback_plan(goal: str, hours_per_week: float, experience_level: str, weeks: int) -> dict:
    """Structured plan when Gemini is unavailable — keeps the app fully usable."""
    out_weeks = []
    for w in range(1, weeks + 1):
        topics = [_fallback_topic(goal, w, d) for d in range(1, 6)]
        out_weeks.append(
            {
                "week_number": w,
                "theme": f"Week {w}: Foundations and practice for {goal}",
                "learning_objectives": [
                    f"Understand key ideas for {goal}",
                    "Apply concepts with short exercises",
                    "Reflect and adjust your approach",
                ],
                "topics": topics,
            }
        )
    return {
        "plan_name": f"{goal} — steady {weeks}-week path",
        "description": f"A calm, consistent plan tailored to {experience_level} learners.",
        "total_weeks": weeks,
        "hours_per_week": hours_per_week,
        "weeks": out_weeks,
    }


def generate_study_plan(goal: str, hours_per_week: float, experience_level: str, weeks: int = 8) -> dict:
    """Ask Gemini to create a fully structured study plan, with offline fallback."""
    if not _api_key:
        logger.warning("GEMINI_API_KEY not set — using built-in study plan template.")
        return build_fallback_plan(goal, hours_per_week, experience_level, weeks)

    prompt = f"""Create a detailed {weeks}-week study plan for this student.

Goal: {goal}
Available time: {hours_per_week} hours per week
Experience level: {experience_level}

Return ONLY valid JSON (no markdown fences):
{{
  "plan_name": "...",
  "description": "One sentence summary of the learning journey",
  "total_weeks": {weeks},
  "hours_per_week": {hours_per_week},
  "weeks": [
    {{
      "week_number": 1,
      "theme": "...",
      "learning_objectives": ["...", "..."],
      "topics": [
        {{
          "day": 1,
          "topic_name": "...",
          "duration_minutes": 45,
          "description": "2-3 sentences about what to study",
          "resource_types": ["video", "reading", "practice"],
          "quiz_questions": [
            {{"question": "...", "options": ["A", "B", "C", "D"], "answer": "A"}},
            {{"question": "...", "options": ["A", "B", "C", "D"], "answer": "B"}},
            {{"question": "...", "options": ["A", "B", "C", "D"], "answer": "C"}},
            {{"question": "...", "options": ["A", "B", "C", "D"], "answer": "D"}},
            {{"question": "...", "options": ["A", "B", "C", "D"], "answer": "A"}}
          ],
          "expected_outcome": "..."
        }}
      ]
    }}
  ]
}}

Make topics specific and engaging for a {experience_level} studying {goal}. Include 5 topics per week (weekdays only)."""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning("Gemini study plan failed (%s); using fallback.", e)
        return build_fallback_plan(goal, hours_per_week, experience_level, weeks)


def _fallback_quiz(topic_name: str) -> list[dict]:
    return [
        {
            "question": f"What is a sensible first step for “{topic_name}”?",
            "options": ["A. Skim without goals", "B. Define one outcome and one practice task", "C. Avoid notes", "D. Study only once a month"],
            "answer": "B",
        },
        {
            "question": "What usually improves retention?",
            "options": ["A. One long cram session", "B. Short sessions with review", "C. Only copying text", "D. No sleep"],
            "answer": "B",
        },
        {
            "question": "How should you use feedback?",
            "options": ["A. Ignore it", "B. Adjust your next practice", "C. Argue with it", "D. Change goals daily"],
            "answer": "B",
        },
        {
            "question": "What is the role of mistakes?",
            "options": ["A. Proof you should quit", "B. Signals to refine understanding", "C. Always bad luck", "D. Ignore"],
            "answer": "B",
        },
        {
            "question": "What supports a calm learning habit?",
            "options": ["A. Random timing", "B. A predictable routine", "C. Constant stress", "D. No breaks"],
            "answer": "B",
        },
    ]


def generate_quiz_for_topic(topic_name: str, description: str) -> list[dict]:
    """Generate a fresh 5-question quiz for any topic on the fly."""
    if not _api_key:
        return _fallback_quiz(topic_name)

    prompt = f"""Create 5 multiple-choice quiz questions about: {topic_name}
Context: {description}

Return ONLY a JSON array (no markdown):
[
  {{
    "question": "...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "answer": "A"
  }}
]"""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning("Gemini quiz failed (%s); using fallback.", e)
        return _fallback_quiz(topic_name)


def generate_motivation_message(student_name: str, streak: int, topic: str, week: int, total_weeks: int) -> str:
    if not _api_key:
        return (
            f"Hi {student_name}, small steps add up. "
            f"You're in week {week} of {total_weeks}; focus on {topic} at a calm pace today."
        )

    prompt = f"""Write a short (2-3 sentences max), warm and calm motivational message for:
- Student name: {student_name}
- Current streak: {streak} days
- Today's topic: {topic}
- Progress: Week {week} of {total_weeks}

Be gentle and encouraging, not hypey. Return only the message text."""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return (response.text or "").strip() or f"Keep going, {student_name} — steady progress matters."
    except Exception as e:
        logger.warning("Gemini motivation failed (%s); using fallback.", e)
        return (
            f"Hi {student_name}, small steps add up. "
            f"You're in week {week} of {total_weeks}; focus on {topic} at a calm pace today."
        )


def generate_intervention(student_name: str, goal: str, avg_quiz_score: float, completion_rate: float, streak: int) -> dict:
    """Gemini analyses performance and returns a structured intervention."""
    if not _api_key:
        return {
            "message": (
                f"{student_name}, it’s okay to slow down. "
                f"Your recent scores are around {int(avg_quiz_score * 100)}% with "
                f"{int(completion_rate * 100)}% completion — we’ll tighten the focus and reduce stress."
            ),
            "actions": [
                "Review one lesson for 20 minutes, then rest.",
                "Rewrite the hardest concept in your own words.",
                "Schedule the next session at the same time tomorrow.",
            ],
            "rationale": "Smaller steps rebuild confidence and consistency.",
            "severity": "medium",
            "add_review_day": True,
            "slow_down_pace": True,
        }

    prompt = f"""A student is struggling with their learning consistency. Generate a compassionate intervention.

Student: {student_name}
Goal: {goal}
Last 7 days avg quiz score: {int(avg_quiz_score * 100)}%
Last 7 days lesson completion: {int(completion_rate * 100)}%
Current streak: {streak} days

Return ONLY JSON (no markdown):
{{
  "message": "Personal, warm message to the student (3-4 sentences)",
  "actions": ["Specific action 1", "Specific action 2", "Specific action 3"],
  "rationale": "Why these actions will help",
  "severity": "low|medium|high",
  "add_review_day": true,
  "slow_down_pace": true
}}"""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning("Gemini intervention failed (%s); using fallback.", e)
        return {
            "message": (
                f"{student_name}, it’s okay to slow down. "
                f"Your recent scores are around {int(avg_quiz_score * 100)}% with "
                f"{int(completion_rate * 100)}% completion — we’ll tighten the focus and reduce stress."
            ),
            "actions": [
                "Review one lesson for 20 minutes, then rest.",
                "Rewrite the hardest concept in your own words.",
                "Schedule the next session at the same time tomorrow.",
            ],
            "rationale": "Smaller steps rebuild confidence and consistency.",
            "severity": "medium",
            "add_review_day": True,
            "slow_down_pace": True,
        }


def generate_chat_reply(student_name: str, goal: str, user_message: str, history_text: str) -> str:
    """Short tutor-style answer for in-app chat."""
    if not _api_key:
        return (
            f"Hi {student_name}. For “{goal}”, try: restate the idea in one sentence, "
            "then work one tiny example. What part feels unclear right now?"
        )

    prompt = f"""You are a calm, concise learning coach for a student.
Student: {student_name}
Learning goal: {goal}

Recent conversation (oldest first):
{history_text}

Latest message: {user_message}

Reply in 2–5 short paragraphs max. Be practical, friendly, and accurate. If unsure, say what to look up."""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return (response.text or "").strip() or "Let’s take this one step at a time. What should we clarify first?"
    except Exception as e:
        logger.warning("Gemini chat failed (%s); using fallback.", e)
        return (
            f"Hi {student_name}. For “{goal}”, try breaking this into a smaller question "
            "and checking one resource from your materials. What’s the first sticking point?"
        )
