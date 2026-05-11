"""
Master Scheduler AI — Vercel Serverless Entry Point
All /api/* routes are handled by this FastAPI app.
Frontend is served as static files from public/ by Vercel.
"""

import os
import sys
import json
import re
from datetime import date, timedelta
from typing import Optional, List

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.database import (
    get_settings, update_settings, get_profile, save_profile,
    create_chat, get_all_chats, get_chat, update_chat_title, delete_chat,
    add_message, get_messages, confirm_schedule_message,
    add_schedule, get_schedules_for_date, get_calendar_events,
    get_today_tasks, update_task_status, get_all_schedules,
    delete_schedules_for_chat, delete_schedule, expire_past_schedules,
    get_history, clear_history, get_subject_colors, update_subject_color,
    get_stress_data, cleanup_orphan_colors, init_db,
    create_schedule_batch, delete_schedule_batch_by_message,
    unconfirm_schedule_message, get_active_schedule_window
)
from backend.ai_engine import (
    get_ai_response, stream_ai_response, generate_chat_title,
    extract_schedule_from_response, clean_response_text
)
from backend.ranking_engine import (
    SubjectEntry, rank_subjects, rerank_after_missed_day,
    generate_daily_study_order, detect_exam_type, get_subject_color
)

app = FastAPI(title="Master Scheduler AI", version="2.1.0")

# CORS — allow all origins for Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Keys from Environment Variables ────────────────────
DEFAULT_OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")


@app.on_event("startup")
async def startup_event():
    """Seed API keys on first startup and expire old schedules."""
    try:
        settings = get_settings()
        if settings and not settings.get('openrouter_api_key'):
            if DEFAULT_OPENROUTER_KEY:
                update_settings(openrouter_api_key=DEFAULT_OPENROUTER_KEY)

        expired = expire_past_schedules()
        if expired > 0:
            print(f"[Startup] Expired {expired} past schedules")
        cleanup_orphan_colors()
    except Exception as e:
        print(f"[Startup] Warning: {e}")


# ─── Request Models ─────────────────────────────────────────

class ChatMessage(BaseModel):
    content: str
    chat_id: Optional[int] = None
    mode: Optional[str] = "student"

class SettingsUpdate(BaseModel):
    openrouter_api_key: Optional[str] = None
    user_name: Optional[str] = None
    user_type: Optional[str] = None

class NewChat(BaseModel):
    title: Optional[str] = "New Chat"
    mode: Optional[str] = "student"

class ConfirmSchedule(BaseModel):
    message_id: int
    chat_id: int
    sessions: List[dict]

class SubjectColorUpdate(BaseModel):
    subject: str
    color: str

class RankingRequest(BaseModel):
    subjects: list

class MissedDayRequest(BaseModel):
    subjects: list
    missed_topics: list
    available_hours: float = 4.0


# ─── Helper ────────────────────────────────────────────────

def _get_openrouter_key():
    """Get OpenRouter API key from settings or environment."""
    settings = get_settings()
    if settings and settings.get('openrouter_api_key'):
        return settings.get('openrouter_api_key')
    return DEFAULT_OPENROUTER_KEY


def _build_calendar_context() -> str:
    """Build a short summary of active calendar blocks for the AI."""
    try:
        today = date.today()
        end_date = today + timedelta(days=7)
        sessions = get_active_schedule_window(today.isoformat(), end_date.isoformat())
    except Exception:
        return ""

    if not sessions:
        return ""

    grouped = {}
    for s in sessions:
        if s.get("session_type") == "break":
            continue
        date_str = s.get("date")
        if not date_str:
            continue
        grouped.setdefault(date_str, []).append(s)

    if not grouped:
        return ""

    lines = []
    for date_str in sorted(grouped.keys()):
        day_sessions = grouped[date_str]
        blocks = []
        for s in day_sessions[:6]:
            start = s.get("start_time", "")
            end = s.get("end_time", "")
            subj = s.get("subject", "Task")
            if start and end:
                blocks.append(f"{start}-{end} {subj}")
        if blocks:
            more = " ..." if len(day_sessions) > 6 else ""
            lines.append(f"- {date_str}: " + "; ".join(blocks) + more)

    if not lines:
        return ""

    return (
        "\n## EXISTING CALENDAR (AVOID CONFLICTS)\n"
        + "\n".join(lines)
        + "\n- Do not overlap these time blocks. If needed, ask for free slots.\n"
    )


# ─── Health ─────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.1.0", "service": "Master Scheduler AI"}


# ─── Settings Endpoints ────────────────────────────────────

@app.get("/api/settings")
async def api_get_settings():
    settings = get_settings()
    if not settings:
        return {"has_openrouter_key": False}
    return {
        "has_openrouter_key": bool(settings.get("openrouter_api_key")),
        "user_name": settings.get("user_name", ""),
        "user_type": settings.get("user_type", "student"),
    }

@app.post("/api/settings")
async def api_update_settings(data: SettingsUpdate):
    updates = {k: v for k, v in data.dict().items() if v is not None}
    if updates:
        update_settings(**updates)
    return {"status": "ok"}


# ─── Profile Endpoints ─────────────────────────────────────

@app.get("/api/profile")
async def api_get_profile():
    return {"profile": get_profile()}

@app.post("/api/profile")
async def api_save_profile(request: Request):
    body = await request.json()
    save_profile(body)
    return {"status": "ok"}


# ─── Chat Endpoints ────────────────────────────────────────

@app.get("/api/chats")
async def api_get_chats():
    chats = get_all_chats()
    return {"chats": chats}

@app.post("/api/chats")
async def api_create_chat(data: NewChat):
    chat_id = create_chat(data.title, data.mode)
    return {"chat_id": chat_id, "title": data.title, "mode": data.mode}

@app.get("/api/chats/{chat_id}")
async def api_get_chat(chat_id: int):
    chat = get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@app.get("/api/chats/{chat_id}/messages")
async def api_get_messages(chat_id: int, limit: int = 100):
    messages = get_messages(chat_id, limit)
    return {"messages": messages}

@app.delete("/api/chats/{chat_id}")
async def api_delete_chat(chat_id: int):
    delete_schedules_for_chat(chat_id)
    delete_chat(chat_id)
    cleanup_orphan_colors()
    return {"status": "ok"}


# ─── Chat Streaming (SSE) ─────────────────────────────────
# Format: { type: 'meta'|'chunk'|'done'|'error', ... }

@app.post("/api/chat/stream")
async def api_chat_stream(data: ChatMessage):
    api_key = _get_openrouter_key()

    if not api_key:
        raise HTTPException(status_code=400, detail="No OpenRouter API key configured.")

    profile = get_profile()
    mode = data.mode or "student"

    # Create or load chat
    chat_id = data.chat_id
    is_new_chat = False
    if not chat_id:
        chat_id = create_chat("New Chat", mode)
        is_new_chat = True

    add_message(chat_id, "user", data.content)
    history = get_messages(chat_id)
    msg_list = [{"role": m["role"], "content": m["content"]} for m in history if m["role"] != "system"]
    calendar_context = _build_calendar_context()

    async def event_stream():
        full_response = ""
        try:
            # Send chat_id first as meta
            yield f"data: {json.dumps({'type': 'meta', 'chat_id': chat_id})}\n\n"

            for chunk in stream_ai_response(api_key, msg_list, mode, profile, calendar_context):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # Process complete response
            schedule_data = extract_schedule_from_response(full_response)
            display_text = clean_response_text(full_response) if schedule_data else full_response
            msg_id = add_message(chat_id, "assistant", display_text, schedule_data)

            # Auto-name new chats
            chat_title = "New Chat"
            if is_new_chat:
                try:
                    chat_title = generate_chat_title(api_key, data.content)
                    update_chat_title(chat_id, chat_title)
                except:
                    chat_title = " ".join(data.content.split()[:5])
                    update_chat_title(chat_id, chat_title)
            else:
                chat = get_chat(chat_id)
                chat_title = chat["title"] if chat else "New Chat"

            # Send final done event with all metadata
            yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id, 'chat_id': chat_id, 'chat_title': chat_title, 'schedule': schedule_data})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ─── Schedule Endpoints ────────────────────────────────────

@app.post("/api/schedule/confirm")
async def api_confirm_schedule(data: ConfirmSchedule):
    batch_id = create_schedule_batch(data.chat_id, data.message_id)
    confirm_schedule_message(data.message_id)
    saved_count = 0
    for s in data.sessions:
        try:
            add_schedule(
                chat_id=data.chat_id,
                subject=s.get("subject", "Unknown"),
                color=s.get("color", get_subject_color(s.get("subject", "Unknown"))),
                date_str=s.get("date", date.today().isoformat()),
                start_time=s.get("start_time", ""),
                end_time=s.get("end_time", ""),
                session_type=s.get("type", "study"),
                topic=s.get("topic", ""),
                priority=s.get("priority", 3),
                batch_id=batch_id
            )
            saved_count += 1
        except Exception as e:
            print(f"Error saving session: {e}")

    cleanup_orphan_colors()
    return {"status": "ok", "saved_count": saved_count, "batch_id": batch_id}

@app.get("/api/schedule/calendar")
async def api_get_calendar():
    calendar = get_calendar_events()
    colors = get_subject_colors()
    return {"calendar": calendar, "subject_colors": colors}

@app.get("/api/schedule/date/{date_str}")
async def api_get_schedule_for_date(date_str: str):
    sessions = get_schedules_for_date(date_str)
    return {"date": date_str, "sessions": sessions}

@app.delete("/api/schedule/{schedule_id}")
async def api_delete_schedule(schedule_id: int):
    delete_schedule(schedule_id)
    cleanup_orphan_colors()
    return {"status": "ok"}

@app.delete("/api/schedule/batch/{message_id}")
async def api_delete_schedule_batch(message_id: int):
    result = delete_schedule_batch_by_message(message_id)
    unconfirm_schedule_message(message_id)
    cleanup_orphan_colors()
    return {
        "status": "ok",
        "deleted_count": result.get("deleted", 0),
        "restored": result.get("restored", False)
    }

@app.post("/api/schedule/expire")
async def api_expire_schedules():
    count = expire_past_schedules()
    cleanup_orphan_colors()
    return {"status": "ok", "expired_count": count}


# ─── Todo Endpoints ────────────────────────────────────────

@app.get("/api/todo/today")
async def api_get_today():
    result = get_today_tasks()
    result["date"] = date.today().isoformat()
    return result

@app.patch("/api/todo/{task_id}")
async def api_update_task(task_id: int, request: Request):
    body = await request.json()
    status = body.get("status", "completed")
    update_task_status(task_id, status)
    return {"status": "ok"}

@app.delete("/api/todo/{task_id}")
async def api_delete_task(task_id: int):
    delete_schedule(task_id)
    cleanup_orphan_colors()
    return {"status": "ok"}


# ─── History Endpoints ─────────────────────────────────────

@app.get("/api/history")
async def api_get_history():
    return get_history()

@app.get("/api/todo/history")
async def api_get_todo_history(limit: int = 50):
    return get_history(limit=limit)

@app.delete("/api/history")
async def api_clear_history():
    clear_history()
    return {"status": "ok"}


# ─── Stress / Health ───────────────────────────────────────

@app.get("/api/health/stress")
async def api_get_stress():
    return get_stress_data()


# ─── Subject Colors ────────────────────────────────────────
# Frontend calls /api/subject-colors (GET and POST)

@app.get("/api/subject-colors")
async def api_get_subject_colors():
    colors = get_subject_colors()
    return {"colors": colors}

@app.post("/api/subject-colors")
async def api_update_subject_color(data: SubjectColorUpdate):
    update_subject_color(data.subject, data.color)
    return {"status": "ok"}


# ─── Ranking Engine ────────────────────────────────────────
# Frontend calls /api/ranking/compute and /api/ranking/missed-day

@app.post("/api/ranking/compute")
async def api_compute_ranking(data: RankingRequest):
    entries = []
    for subj in data.subjects:
        entry = SubjectEntry(
            subject=subj.get("subject", "Unknown"),
            topic=subj.get("topic", subj.get("subject", "Unknown")),
            exam_type=subj.get("exam_type", detect_exam_type(subj.get("subject", ""))),
            exam_date=subj.get("exam_date", ""),
            user_confidence=subj.get("confidence", 5),
            revision_status=subj.get("revision_status", "needs_revision"),
            user_priority=subj.get("priority", "medium"),
            estimated_hours=subj.get("estimated_hours", 2.0),
            color=subj.get("color", get_subject_color(subj.get("subject", ""))),
        )
        entries.append(entry)
    result = rank_subjects(entries)
    return result

@app.post("/api/ranking/missed-day")
async def api_handle_missed_day(data: MissedDayRequest):
    entries = []
    for subj in data.subjects:
        entry = SubjectEntry(
            subject=subj.get("subject", "Unknown"),
            topic=subj.get("topic", subj.get("subject", "Unknown")),
            exam_type=subj.get("exam_type", "school"),
            exam_date=subj.get("exam_date", ""),
            user_confidence=subj.get("confidence", 5),
            revision_status=subj.get("revision_status", "needs_revision"),
            user_priority=subj.get("priority", "medium"),
            estimated_hours=subj.get("estimated_hours", 2.0),
        )
        entries.append(entry)
    result = rerank_after_missed_day(entries, data.missed_topics, data.available_hours)
    return result
