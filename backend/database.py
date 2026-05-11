"""
Supabase Database Layer for Master Scheduler AI
Replaces SQLite with Supabase PostgreSQL via supabase-py client.
Tables: settings, chats, messages, schedules, subject_colors, schedule_history
"""

import json
import os
import re
from datetime import datetime, date, timedelta
from supabase import create_client, Client

# ─── Supabase Client ────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_client: Client = None


def get_client() -> Client:
    """Get or create Supabase client (singleton)."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY environment variables are required."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def init_db():
    """Ensure settings row exists. Tables are created via SQL migration."""
    sb = get_client()
    # Check if settings row exists
    result = sb.table("settings").select("id").eq("id", 1).execute()
    if not result.data:
        sb.table("settings").insert({"id": 1}).execute()


# ─── Settings ───────────────────────────────────────────────

def get_settings():
    sb = get_client()
    result = sb.table("settings").select("*").eq("id", 1).execute()
    if result.data:
        return result.data[0]
    return None


def update_settings(**kwargs):
    allowed = ['openrouter_api_key', 'user_name', 'user_type', 'profile_json']
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    fields['updated_at'] = datetime.utcnow().isoformat()
    sb = get_client()
    sb.table("settings").update(fields).eq("id", 1).execute()


# ─── Profile ────────────────────────────────────────────────

def get_profile():
    """Get user profile data."""
    settings = get_settings()
    if settings and settings.get('profile_json'):
        try:
            profile = json.loads(settings['profile_json'])
            profile['name'] = settings.get('user_name', '')
            profile['user_type'] = settings.get('user_type', 'student')
            return profile
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        'name': settings.get('user_name', '') if settings else '',
        'user_type': settings.get('user_type', 'student') if settings else 'student'
    }


def save_profile(profile_data: dict):
    """Save user profile data."""
    name = profile_data.pop('name', '')
    user_type = profile_data.pop('user_type', 'student')
    profile_json = json.dumps(profile_data)
    update_settings(
        user_name=name,
        user_type=user_type,
        profile_json=profile_json
    )


# ─── Chats ──────────────────────────────────────────────────

def create_chat(title="New Chat", mode="student"):
    sb = get_client()
    result = sb.table("chats").insert(
        {"title": title, "mode": mode}
    ).execute()
    return result.data[0]['id']


def get_all_chats():
    sb = get_client()
    result = sb.table("chats").select("*").order(
        "updated_at", desc=True
    ).execute()
    return result.data


def get_chat(chat_id):
    sb = get_client()
    result = sb.table("chats").select("*").eq("id", chat_id).execute()
    return result.data[0] if result.data else None


def update_chat_title(chat_id, title):
    sb = get_client()
    sb.table("chats").update(
        {"title": title, "updated_at": datetime.utcnow().isoformat()}
    ).eq("id", chat_id).execute()


def delete_chat(chat_id):
    sb = get_client()
    sb.table("chats").delete().eq("id", chat_id).execute()


# ─── Messages ───────────────────────────────────────────────

def add_message(chat_id, role, content, schedule_json=None):
    sb = get_client()
    data = {
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "schedule_json": json.dumps(schedule_json) if schedule_json else None
    }
    result = sb.table("messages").insert(data).execute()
    # Update chat timestamp
    sb.table("chats").update(
        {"updated_at": datetime.utcnow().isoformat()}
    ).eq("id", chat_id).execute()
    return result.data[0]['id']


def get_messages(chat_id, limit=100):
    sb = get_client()
    result = sb.table("messages").select("*").eq(
        "chat_id", chat_id
    ).order("created_at").limit(limit).execute()

    messages = []
    for d in result.data:
        if d.get('schedule_json'):
            try:
                d['schedule_json'] = json.loads(d['schedule_json'])
            except:
                pass
        messages.append(d)
    return messages


def confirm_schedule_message(message_id):
    sb = get_client()
    sb.table("messages").update({"confirmed": 1}).eq("id", message_id).execute()


# ─── Schedules ──────────────────────────────────────────────

def add_schedule(chat_id, subject, color, date_str, start_time, end_time,
                 session_type="study", topic="", priority=3):
    sb = get_client()
    data = {
        "chat_id": chat_id,
        "subject": subject,
        "color": color,
        "date": date_str,
        "start_time": start_time,
        "end_time": end_time,
        "session_type": session_type,
        "topic": topic,
        "priority": priority
    }
    result = sb.table("schedules").insert(data).execute()

    # Upsert subject color
    sb.table("subject_colors").upsert(
        {"subject": subject, "color": color, "updated_at": datetime.utcnow().isoformat()},
        on_conflict="subject"
    ).execute()

    return result.data[0]['id']


def get_schedules_for_date(date_str):
    sb = get_client()
    result = sb.table("schedules").select("*").eq(
        "date", date_str
    ).order("start_time").execute()
    return result.data


def get_calendar_events():
    """Get all dates that have scheduled events with their subject colors.
       Excludes breaks from dot display. Marks exam dates."""
    sb = get_client()
    result = sb.table("schedules").select(
        "date, subject, color, session_type"
    ).order("date").execute()

    calendar = {}
    for row in result.data:
        dt = row['date']
        if dt not in calendar:
            calendar[dt] = {"subjects": [], "has_exam": False}

        if row['session_type'] not in ('break',):
            # Deduplicate subject entries per date
            existing = [s['subject'] for s in calendar[dt]['subjects']]
            if row['subject'] not in existing:
                calendar[dt]["subjects"].append({
                    'subject': row['subject'],
                    'color': row['color'],
                    'type': row['session_type'],
                    'count': 1
                })
            else:
                # Increment count
                for s in calendar[dt]['subjects']:
                    if s['subject'] == row['subject']:
                        s['count'] += 1
                        break

        if row['session_type'] in ('exam', 'test', 'mock'):
            calendar[dt]["has_exam"] = True

    return calendar


def get_today_tasks():
    """Get today's tasks including nearby dates for context."""
    today = date.today().isoformat()
    sb = get_client()

    # Today's tasks
    result = sb.table("schedules").select("*").eq(
        "date", today
    ).order("start_time").execute()
    tasks = result.data

    pending = sum(1 for t in tasks if t['status'] == 'pending')
    completed = sum(1 for t in tasks if t['status'] == 'completed')
    in_progress = sum(1 for t in tasks if t['status'] == 'in_progress')
    missed = sum(1 for t in tasks if t['status'] == 'missed')

    # Get overdue tasks from past dates
    overdue_result = sb.table("schedules").select("*").lt(
        "date", today
    ).eq("status", "pending").neq(
        "session_type", "break"
    ).order("date").order("start_time").execute()
    overdue = overdue_result.data

    # Get next upcoming task
    next_task = None
    for t in tasks:
        if t['status'] == 'pending' and t['session_type'] != 'break':
            next_task = t
            break

    return {
        "tasks": tasks,
        "overdue": overdue,
        "next_task": next_task,
        "stats": {
            "total": len(tasks),
            "pending": pending,
            "completed": completed,
            "in_progress": in_progress,
            "missed": missed,
        }
    }


def update_task_status(task_id, status):
    sb = get_client()
    sb.table("schedules").update({"status": status}).eq("id", task_id).execute()
    if status == 'completed':
        move_schedule_to_history(task_id, 'completed')


def get_all_schedules():
    sb = get_client()
    result = sb.table("schedules").select("*").order("date").order("start_time").execute()
    return result.data


def delete_schedules_for_chat(chat_id):
    sb = get_client()
    sb.table("schedules").delete().eq("chat_id", chat_id).execute()


def delete_schedule(schedule_id):
    """Delete a single schedule and move to history."""
    sb = get_client()
    result = sb.table("schedules").select("*").eq("id", schedule_id).execute()
    if result.data:
        d = result.data[0]
        sb.table("schedule_history").insert({
            "original_schedule_id": d['id'],
            "chat_id": d['chat_id'],
            "subject": d['subject'],
            "color": d['color'],
            "date": d['date'],
            "start_time": d['start_time'],
            "end_time": d['end_time'],
            "session_type": d['session_type'],
            "topic": d['topic'],
            "status": d['status'],
            "priority": d['priority'],
            "reason": "deleted"
        }).execute()
        sb.table("schedules").delete().eq("id", schedule_id).execute()


def expire_past_schedules():
    """Move expired (past date, still pending) schedules to history and mark as missed."""
    today = date.today().isoformat()
    sb = get_client()

    # Get expired pending schedules (non-break)
    result = sb.table("schedules").select("*").lt(
        "date", today
    ).eq("status", "pending").neq("session_type", "break").execute()

    moved_count = 0
    for d in result.data:
        sb.table("schedule_history").insert({
            "original_schedule_id": d['id'],
            "chat_id": d['chat_id'],
            "subject": d['subject'],
            "color": d['color'],
            "date": d['date'],
            "start_time": d['start_time'],
            "end_time": d['end_time'],
            "session_type": d['session_type'],
            "topic": d['topic'],
            "status": "missed",
            "priority": d['priority'],
            "reason": "expired"
        }).execute()
        sb.table("schedules").update({"status": "missed"}).eq("id", d['id']).execute()
        moved_count += 1

    # Remove old break sessions
    sb.table("schedules").delete().lt("date", today).eq("session_type", "break").execute()

    return moved_count


def move_schedule_to_history(schedule_id, reason='completed'):
    """Move a schedule entry to the history table."""
    sb = get_client()
    result = sb.table("schedules").select("*").eq("id", schedule_id).execute()
    if result.data:
        d = result.data[0]
        sb.table("schedule_history").insert({
            "original_schedule_id": d['id'],
            "chat_id": d['chat_id'],
            "subject": d['subject'],
            "color": d['color'],
            "date": d['date'],
            "start_time": d['start_time'],
            "end_time": d['end_time'],
            "session_type": d['session_type'],
            "topic": d['topic'],
            "status": d['status'],
            "priority": d['priority'],
            "reason": reason
        }).execute()


# ─── History ────────────────────────────────────────────────

def get_history(limit=50):
    """Get schedule history (completed/expired/deleted tasks)."""
    sb = get_client()
    result = sb.table("schedule_history").select("*").order(
        "moved_at", desc=True
    ).limit(limit).execute()

    history = result.data
    stats = {
        'total': len(history),
        'completed': sum(1 for h in history if h.get('reason') == 'completed'),
        'expired': sum(1 for h in history if h.get('reason') == 'expired'),
        'deleted': sum(1 for h in history if h.get('reason') == 'deleted'),
    }
    return {"history": history, "stats": stats}


def clear_history():
    """Clear all history entries."""
    sb = get_client()
    # Delete all rows - supabase needs a filter, use gt id 0
    sb.table("schedule_history").delete().gt("id", 0).execute()


# ─── Subject Colors ─────────────────────────────────────────

def get_subject_colors():
    """Get all subject → color mappings."""
    sb = get_client()
    result = sb.table("subject_colors").select(
        "subject, color"
    ).order("subject").execute()
    return {r['subject']: r['color'] for r in result.data}


def update_subject_color(subject: str, new_color: str):
    """Update a subject's color globally."""
    sb = get_client()
    sb.table("subject_colors").upsert(
        {"subject": subject, "color": new_color, "updated_at": datetime.utcnow().isoformat()},
        on_conflict="subject"
    ).execute()
    sb.table("schedules").update({"color": new_color}).eq("subject", subject).execute()


def remove_subject_color(subject: str):
    """Remove a subject color when no more schedules exist for it."""
    sb = get_client()
    result = sb.table("schedules").select("id").eq("subject", subject).limit(1).execute()
    if not result.data:
        sb.table("subject_colors").delete().eq("subject", subject).execute()


def cleanup_orphan_colors():
    """Remove subject colors that have no active schedules."""
    sb = get_client()
    colors = sb.table("subject_colors").select("subject").execute()
    schedules = sb.table("schedules").select("subject").execute()

    active_subjects = set(r['subject'] for r in schedules.data)
    protected = {'Break', 'Long Break'}

    for c in colors.data:
        if c['subject'] not in active_subjects and c['subject'] not in protected:
            sb.table("subject_colors").delete().eq("subject", c['subject']).execute()


def get_stress_data():
    """Calculate stress metrics based on schedule density and completion."""
    today = date.today().isoformat()
    sb = get_client()

    # All non-break schedules
    all_result = sb.table("schedules").select("*").neq("session_type", "break").execute()
    all_schedules = all_result.data

    total_all = len(all_schedules)
    upcoming = sum(1 for s in all_schedules if s['date'] >= today)
    completed = sum(1 for s in all_schedules if s['status'] == 'completed')
    missed = sum(1 for s in all_schedules if s['status'] == 'missed')
    overdue = sum(1 for s in all_schedules if s['status'] == 'pending' and s['date'] < today)

    # Calculate study hours
    upcoming_study = [s for s in all_schedules if s['date'] >= today and s['session_type'] == 'study']
    daily_hours = {}
    total_study_minutes = 0
    for s in upcoming_study:
        try:
            start = datetime.strptime(s['start_time'], "%H:%M")
            end = datetime.strptime(s['end_time'], "%H:%M")
            mins = (end - start).total_seconds() / 60
            total_study_minutes += mins
            daily_hours[s['date']] = daily_hours.get(s['date'], 0) + mins
        except:
            pass

    # Get profile for available hours
    profile = get_profile()
    daily_available = 6
    try:
        dh = profile.get('daily_study_hours', '')
        if dh:
            nums = re.findall(r'\d+', str(dh))
            if nums:
                daily_available = max(float(nums[-1]), 2)
    except:
        pass

    # Fullness score
    if not daily_hours:
        fullness = 0
    else:
        avg_daily_mins = sum(daily_hours.values()) / max(len(daily_hours), 1)
        fullness = min(100, int((avg_daily_mins / (daily_available * 60)) * 100))

    # Stress calculation
    if total_all == 0:
        stress = 0
        level = "green"
        label = "No tasks yet 📭"
    else:
        overdue_factor = min(50, int(((missed + overdue) / max(total_all, 1)) * 100))
        stress = min(100, int((overdue_factor * 0.4 + fullness * 0.6)))

        if stress < 30:
            level = "green"
            label = "You're on track! 🎯"
        elif stress < 50:
            level = "yellow"
            label = "Moderate workload ⚡"
        elif stress < 70:
            level = "orange"
            label = "Getting packed! ⚠️"
        else:
            level = "red"
            label = "Schedule overload! 🔴"

    num_days = len(daily_hours)
    total_hours = round(total_study_minutes / 60, 1)
    avg_hrs = round(total_hours / max(num_days, 1), 1)

    return {
        "score": stress,
        "fullness": fullness,
        "level": level,
        "label": label,
        "total": total_all,
        "completed": completed,
        "missed": missed,
        "overdue": overdue,
        "upcoming": upcoming,
        "total_study_hours": total_hours,
        "avg_daily_hours": avg_hrs,
        "scheduled_days": num_days,
    }


# Initialize on import
try:
    init_db()
except Exception:
    # Will fail if env vars not set (e.g., during build)
    pass
