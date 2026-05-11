"""
Scientific Scheduling Engine for Master Scheduler AI
Implements break ratios, priority weighting, and recovery planning.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
import json


# ─── Break Ratio Configurations ─────────────────────────────

BREAK_PROFILES = {
    "1hr": {
        "total_minutes": 60,
        "session_length": 27.5,
        "short_break": 5,
        "long_break": 0,
        "long_break_interval": 0,
        "description": "2 × 27.5min study + 5min break"
    },
    "2hr": {
        "total_minutes": 120,
        "session_length": 27.5,
        "short_break": 5,
        "long_break": 0,
        "long_break_interval": 0,
        "description": "27.5min sessions + 5min break after every session"
    },
    "3-4hr": {
        "total_minutes": 210,  # 3.5hr average
        "session_length": 27.5,
        "short_break": 5,
        "long_break": 10,
        "long_break_interval": 120,  # every 2 hours
        "description": "27.5min sessions + 5min breaks + 10min every 2hrs"
    },
    "5-8hr": {
        "total_minutes": 390,  # 6.5hr average
        "session_length": 50,
        "short_break": 10,
        "long_break": 30,
        "long_break_interval": 150,  # every 2.5 hours
        "description": "50min sessions + 10min breaks + 30min every 2.5hrs + meals"
    },
    "9-12hr": {
        "total_minutes": 630,  # 10.5hr average
        "session_length": 50,
        "short_break": 10,
        "long_break": 45,
        "long_break_interval": 180,  # every 3 hours
        "description": "50min sessions + 10min breaks + 45min every 3hrs, split AM/PM"
    }
}


def get_break_profile(total_hours: float) -> dict:
    """Get the appropriate break profile for given study hours."""
    if total_hours <= 1.5:
        return BREAK_PROFILES["1hr"]
    elif total_hours <= 2.5:
        return BREAK_PROFILES["2hr"]
    elif total_hours <= 4.5:
        return BREAK_PROFILES["3-4hr"]
    elif total_hours <= 8.5:
        return BREAK_PROFILES["5-8hr"]
    else:
        return BREAK_PROFILES["9-12hr"]


def generate_time_blocks(start_time: str, total_hours: float, subject: str,
                         color: str, topics: List[str], date_str: str,
                         priority: int = 3) -> List[Dict]:
    """
    Generate study session blocks with proper breaks.
    Returns a list of session dictionaries.
    """
    profile = get_break_profile(total_hours)
    sessions = []
    
    current = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
    end_limit = current + timedelta(hours=total_hours)
    
    session_len = timedelta(minutes=profile["session_length"])
    short_break = timedelta(minutes=profile["short_break"])
    long_break = timedelta(minutes=profile["long_break"]) if profile["long_break"] else None
    long_interval = profile["long_break_interval"]
    
    elapsed_since_long = 0
    topic_idx = 0
    
    while current + session_len <= end_limit:
        # Check if we need a long break
        if long_break and long_interval and elapsed_since_long >= long_interval:
            sessions.append({
                "subject": "Long Break",
                "color": "#9CA3AF",
                "date": date_str,
                "start_time": current.strftime("%H:%M"),
                "end_time": (current + long_break).strftime("%H:%M"),
                "type": "break",
                "topic": "Long break — stretch, walk, refresh",
                "priority": 0
            })
            current += long_break
            elapsed_since_long = 0
            continue
        
        # Study session
        topic = topics[topic_idx % len(topics)] if topics else subject
        session_end = min(current + session_len, end_limit)
        
        sessions.append({
            "subject": subject,
            "color": color,
            "date": date_str,
            "start_time": current.strftime("%H:%M"),
            "end_time": session_end.strftime("%H:%M"),
            "type": "study",
            "topic": topic,
            "priority": priority
        })
        
        elapsed_since_long += profile["session_length"]
        current = session_end
        topic_idx += 1
        
        # Short break after session
        if current + short_break <= end_limit:
            sessions.append({
                "subject": "Break",
                "color": "#9CA3AF",
                "date": date_str,
                "start_time": current.strftime("%H:%M"),
                "end_time": (current + short_break).strftime("%H:%M"),
                "type": "break",
                "topic": "Short break",
                "priority": 0
            })
            current += short_break
            elapsed_since_long += profile["short_break"]
    
    return sessions


# ─── Priority Engine ────────────────────────────────────────

PRIORITY_KEYWORDS = {
    5: ["jee", "neet", "competitive", "entrance", "olympiad", "sat", "gre", "gate", "cat"],
    4: ["pre-board", "preboard", "board", "final", "annual", "semester"],
    3: ["school", "mid-term", "midterm", "unit test", "class test"],
    2: ["tuition", "coaching", "weekly", "practice"],
    1: ["mock", "sample", "self-test", "revision"]
}


def infer_priority(exam_description: str) -> int:
    """Infer exam priority from description. Returns 1-5."""
    desc_lower = exam_description.lower()
    for priority, keywords in sorted(PRIORITY_KEYWORDS.items(), reverse=True):
        for kw in keywords:
            if kw in desc_lower:
                return priority
    return 3  # Default medium priority


# ─── Biological Constraints ─────────────────────────────────

DEFAULT_CONSTRAINTS = {
    "wake_up": "07:00",
    "sleep_by": "23:00",
    "dinner_start": "19:30",
    "dinner_end": "20:30",
    "lunch_start": "13:00",
    "lunch_end": "14:00",
    "min_session_gap": 5,  # minutes between sessions
}


def apply_biological_constraints(sessions: List[Dict], constraints: dict = None) -> List[Dict]:
    """Filter or adjust sessions to respect biological needs."""
    c = constraints or DEFAULT_CONSTRAINTS
    
    filtered = []
    for s in sessions:
        start = s["start_time"]
        end = s["end_time"]
        
        # Skip sessions during dinner
        if _times_overlap(start, end, c["dinner_start"], c["dinner_end"]):
            continue
        
        # Skip sessions during lunch
        if _times_overlap(start, end, c["lunch_start"], c["lunch_end"]):
            continue
        
        # Skip sessions past sleep time
        if start >= c["sleep_by"]:
            continue
        
        # Skip sessions before wake up
        if end <= c["wake_up"]:
            continue
        
        filtered.append(s)
    
    return filtered


def _times_overlap(s1: str, e1: str, s2: str, e2: str) -> bool:
    """Check if two time ranges overlap."""
    return s1 < e2 and s2 < e1


# ─── Recovery Planning ──────────────────────────────────────

def generate_recovery_options(missed_sessions: List[Dict], 
                              available_hours: float,
                              upcoming_dates: List[str]) -> Dict:
    """Generate recovery options when user misses study sessions."""
    
    total_missed_minutes = sum(
        _duration_minutes(s["start_time"], s["end_time"]) 
        for s in missed_sessions if s["type"] == "study"
    )
    
    high_priority = [s for s in missed_sessions if s.get("priority", 3) >= 4]
    low_priority = [s for s in missed_sessions if s.get("priority", 3) < 3]
    medium_priority = [s for s in missed_sessions if s.get("priority", 3) in [3]]
    
    options = {
        "missed_summary": {
            "total_sessions": len([s for s in missed_sessions if s["type"] == "study"]),
            "total_minutes": total_missed_minutes,
            "subjects": list(set(s["subject"] for s in missed_sessions if s["type"] == "study"))
        },
        "options": [
            {
                "id": "A",
                "label": "Shift full schedule forward",
                "description": "Move everything forward by the missed time. Safest but extends your timeline."
            },
            {
                "id": "B",
                "label": "Compress remaining schedule",
                "description": f"Fit {total_missed_minutes}min of missed work into remaining days with slightly longer sessions."
            },
            {
                "id": "C",
                "label": "Skip low-priority tasks",
                "description": f"Drop {len(low_priority)} lower-priority tasks and focus on what matters most."
            },
            {
                "id": "D",
                "label": "Focus only on high-priority exams",
                "description": f"Prioritize {len(high_priority)} critical sessions. Best for time crunch."
            }
        ]
    }
    
    return options


def _duration_minutes(start: str, end: str) -> float:
    """Get duration in minutes between two HH:MM time strings."""
    s = datetime.strptime(start, "%H:%M")
    e = datetime.strptime(end, "%H:%M")
    return (e - s).total_seconds() / 60


# ─── Teacher Mode Scheduling ────────────────────────────────

DEFAULT_HOLIDAYS = {5, 6}  # Saturday=5, Sunday=6 (weekday indices)


def generate_teacher_schedule(num_tests: int, 
                               window_days: int,
                               start_date: str,
                               blocked_days: List[str] = None,
                               holidays: set = None) -> List[Dict]:
    """
    Schedule N tests within a window of days, respecting holidays and blocked days.
    """
    if holidays is None:
        holidays = DEFAULT_HOLIDAYS
    if blocked_days is None:
        blocked_days = []
    
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    blocked_set = set(blocked_days)
    
    available_dates = []
    for i in range(window_days):
        d = start + timedelta(days=i)
        if d.weekday() not in holidays and d.isoformat() not in blocked_set:
            available_dates.append(d)
    
    if len(available_dates) < num_tests:
        return {"error": f"Not enough available days. Need {num_tests}, have {len(available_dates)}."}
    
    # Spread tests evenly across available days
    step = max(1, len(available_dates) // num_tests)
    scheduled = []
    for i in range(num_tests):
        idx = min(i * step, len(available_dates) - 1)
        d = available_dates[idx]
        scheduled.append({
            "subject": f"Test {i+1}",
            "color": "#EF4444",
            "date": d.isoformat(),
            "start_time": "09:00",
            "end_time": "10:00",
            "type": "exam",
            "topic": f"Class Test {i+1}",
            "priority": 4
        })
    
    return scheduled
