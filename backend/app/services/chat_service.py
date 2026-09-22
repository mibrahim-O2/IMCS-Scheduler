"""Function-calling chatbot: Gemini picks a real database query, we run it, Gemini phrases
the answer from the real result. Not RAG there is no document store or embedding search
anywhere in this file; every answer traces back to a live SQL query against the same
tables the rest of the app uses. See docs/PROJECT_ARCHITECTURE.md §8.

Each `get_*` function below is plain, independently callable Python real, testable
without Gemini at all (and self-tested that way; see docs/PROJECT_AUDIT.md Phase 10).
Gemini's only job is choosing which one(s) to call from a natural-language question and
turning the structured result back into a sentence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Classroom, Course, Teacher, Timetable, TimetableSession
from app.scheduler.chromosome import DAYS, TIME_SLOTS

WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
GEMINI_MODEL = "gemini-3.6-flash"


class ChatUnavailableError(Exception):
    """Raised when the chat endpoint can't run a real Gemini turn (e.g. no API key)."""


def _latest_timetable_id(db: Session) -> int | None:
    # "Current" data, system-wide: the single most recently generated Timetable. Nothing is
    # ever marked `published` yet (out of scope so far, docs/PROJECT_AUDIT.md), so treating
    # the newest generated run as "what's currently scheduled" is the honest choice rather
    # than the functions always answering "nothing generated" against a status that
    # nothing in this database has ever been given.
    return db.scalar(select(Timetable.id).order_by(Timetable.created_at.desc()).limit(1))


def _current_day_and_slot() -> tuple[str, tuple[str, str, str] | None]:
    # The real server clock, mapped onto the same Mon-Fri/6-period grid every generated
    # timetable uses. A weekend or an out-of-hours moment correctly has no matching slot.
    now = datetime.now()
    day = WEEKDAY_NAMES[now.weekday()]
    current = now.strftime("%H:%M")
    slot = next((s for s in TIME_SLOTS if s[1] <= current < s[2]), None)
    return day, slot


def _session_rows(db: Session, timetable_id: int, **filters: Any) -> list[dict]:
    # Every TimetableSession in one timetable, joined with the real names the chatbot's
    # answers need (course, teacher, room) shared by every get_* function below.
    statement = select(TimetableSession).where(TimetableSession.timetable_id == timetable_id)
    for column, value in filters.items():
        statement = statement.where(getattr(TimetableSession, column) == value)
    sessions = db.scalars(statement).all()

    courses = {row.id: row for row in db.scalars(select(Course))}
    teachers = {row.id: row for row in db.scalars(select(Teacher))}
    rooms = {row.id: row for row in db.scalars(select(Classroom))}
    return [
        {
            "day": session.day,
            "start_time": session.start_time.strftime("%H:%M"),
            "end_time": session.end_time.strftime("%H:%M"),
            "course_name": courses[session.course_id].name,
            "teacher_name": teachers[session.teacher_id].full_name,
            "room_name": rooms[session.room_id].name,
            "is_lab": session.is_lab,
        }
        for session in sessions
    ]


def get_current_class(db: Session, room_or_teacher: str) -> dict:
    # "Who's teaching right now" / "what's in Room 05 right now" real server time, matched
    # against the single most recent generated timetable.
    day, slot = _current_day_and_slot()
    if day not in DAYS:
        return {"found": False, "reason": f"Today is {day}. Classes only run Monday to Friday."}
    if slot is None:
        now = datetime.now().strftime("%H:%M")
        return {"found": False, "reason": f"It's {now} on {day}, outside class hours (08:30-13:30)."}

    timetable_id = _latest_timetable_id(db)
    if timetable_id is None:
        return {"found": False, "reason": "No timetable has been generated yet."}

    rows = [
        row
        for row in _session_rows(db, timetable_id, day=day)
        if row["start_time"] == slot[1]
        and room_or_teacher.strip().lower() in f"{row['room_name']} {row['teacher_name']}".lower()
    ]
    if not rows:
        return {"found": False, "reason": f"Nothing matching '{room_or_teacher}' is scheduled right now ({day} {slot[0]})."}
    return {"found": True, "day": day, "time": slot[0], "sessions": rows}


def get_teacher_schedule(db: Session, teacher_name: str) -> dict:
    # A named teacher's real weekly schedule, from the single most recent generated
    # timetable that actually includes them (mirrors the teacher lookup page's own logic,
    # docs/PROJECT_AUDIT.md Phase 10, so the chatbot and that page never disagree).
    teacher = db.scalar(select(Teacher).where(Teacher.full_name.ilike(f"%{teacher_name.strip()}%")))
    if teacher is None:
        return {"found": False, "reason": f"No teacher matching '{teacher_name}' is on record."}

    timetable_id = db.scalar(
        select(Timetable.id)
        .join(TimetableSession, TimetableSession.timetable_id == Timetable.id)
        .where(TimetableSession.teacher_id == teacher.id)
        .order_by(Timetable.created_at.desc())
        .limit(1)
    )
    if timetable_id is None:
        return {
            "found": False,
            "reason": f"No timetable has been generated yet for any division {teacher.full_name} teaches in.",
        }

    rows = _session_rows(db, timetable_id, teacher_id=teacher.id)
    return {"found": True, "teacher_name": teacher.full_name, "sessions": rows}


def get_room_status(db: Session, room_name: str) -> dict:
    # Is this room occupied right now, and by what real server time, latest timetable.
    room = db.scalar(select(Classroom).where(Classroom.name.ilike(f"%{room_name.strip()}%")))
    if room is None:
        return {"found": False, "reason": f"No room matching '{room_name}' is on record."}

    day, slot = _current_day_and_slot()
    if day not in DAYS or slot is None:
        return {"found": True, "room_name": room.name, "occupied": False, "reason": "Outside class hours right now."}

    timetable_id = _latest_timetable_id(db)
    if timetable_id is None:
        return {"found": True, "room_name": room.name, "occupied": False, "reason": "No timetable has been generated yet."}

    rows = [row for row in _session_rows(db, timetable_id, day=day, room_id=room.id) if row["start_time"] == slot[1]]
    if not rows:
        return {"found": True, "room_name": room.name, "occupied": False, "day": day, "time": slot[0]}
    return {"found": True, "room_name": room.name, "occupied": True, "day": day, "time": slot[0], "session": rows[0]}


def get_free_rooms(db: Session, day: str, time: str) -> dict:
    # Every real room not booked at a given day + time, checked against the single most
    # recent generated timetable. `time` is matched to the class period it falls in.
    day = day.strip()[:3].title()
    if day not in DAYS:
        return {"found": False, "reason": f"'{day}' isn't a real class day (Mon-Fri)."}

    slot = next((s for s in TIME_SLOTS if s[1] <= time < s[2]), None)
    if slot is None:
        return {"found": False, "reason": f"'{time}' doesn't fall in any real class period (08:30-13:30)."}

    timetable_id = _latest_timetable_id(db)
    all_rooms = {row.id: row.name for row in db.scalars(select(Classroom))}
    if timetable_id is None:
        return {"found": True, "day": day, "time": slot[0], "free_rooms": sorted(all_rooms.values())}

    busy_room_ids = {
        session.room_id
        for session in db.scalars(
            select(TimetableSession).where(TimetableSession.timetable_id == timetable_id, TimetableSession.day == day)
        )
        if session.start_time.strftime("%H:%M") == slot[1]
    }
    free = sorted(name for room_id, name in all_rooms.items() if room_id not in busy_room_ids)
    return {"found": True, "day": day, "time": slot[0], "free_rooms": free}


# Gemini's function-calling schema for the four query tools above one entry per function,
# matching its name/parameters exactly so genai can dispatch a call straight into FUNCTIONS.
_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="get_current_class",
                description="What class (course, teacher, room) is happening right now, for a room name or teacher name.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"room_or_teacher": types.Schema(type=types.Type.STRING)},
                    required=["room_or_teacher"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_teacher_schedule",
                description="A named teacher's real weekly class schedule.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"teacher_name": types.Schema(type=types.Type.STRING)},
                    required=["teacher_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_room_status",
                description="Whether a named room is occupied right now, and by what.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"room_name": types.Schema(type=types.Type.STRING)},
                    required=["room_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_free_rooms",
                description="Every room free at a given day and time, e.g. day='Tuesday', time='10:00'.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "day": types.Schema(type=types.Type.STRING),
                        "time": types.Schema(type=types.Type.STRING, description="24-hour HH:MM"),
                    },
                    required=["day", "time"],
                ),
            ),
        ]
    )
]

FUNCTIONS = {
    "get_current_class": get_current_class,
    "get_teacher_schedule": get_teacher_schedule,
    "get_room_status": get_room_status,
    "get_free_rooms": get_free_rooms,
}

SYSTEM_INSTRUCTION = (
    "You answer questions about a university department's real class schedule by calling the "
    "functions you've been given never guess or invent a schedule fact yourself. If a function "
    "reports nothing found (e.g. no timetable generated yet, or no matching teacher/room), say "
    "that plainly instead of making up an answer. Keep answers short and factual."
)


def run_chat(db: Session, message: str, history: list[dict[str, str]]) -> str:
    # One chat turn: sends the question (plus prior turns) to Gemini with the four tools
    # above, executes whichever function(s) Gemini picks against the real database, and
    # asks Gemini to phrase the final answer from that real result.
    api_key = get_settings().gemini_api_key
    if not api_key:
        raise ChatUnavailableError(
            "The chatbot needs a Gemini API key. Set GEMINI_API_KEY in backend/.env "
            "(a free key is available at https://aistudio.google.com/apikey) and restart the server."
        )

    try:
        client = genai.Client(api_key=api_key)
        contents = [
            types.Content(role="user" if turn["role"] == "user" else "model", parts=[types.Part(text=turn["text"])])
            for turn in history
        ]
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

        config = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, tools=_TOOLS)
        response = client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)

        # Gemini may ask for one or more function calls before it's ready to answer in
        # words; keep executing them and feeding the real results back until it stops.
        for _ in range(5):
            calls = [part.function_call for part in response.candidates[0].content.parts if part.function_call]
            if not calls:
                break
            contents.append(response.candidates[0].content)
            result_parts = []
            for call in calls:
                handler = FUNCTIONS.get(call.name)
                result = handler(db, **call.args) if handler else {"error": f"Unknown function {call.name}"}
                result_parts.append(types.Part(function_response=types.FunctionResponse(name=call.name, response=result)))
            contents.append(types.Content(role="user", parts=result_parts))
            response = client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)

        return response.text or "I couldn't work out an answer to that."
    except ChatUnavailableError:
        raise
    except Exception as exc:  # the Gemini SDK raises several distinct error types for a bad/invalid key
        raise ChatUnavailableError(f"Couldn't reach Gemini: {exc}") from exc
