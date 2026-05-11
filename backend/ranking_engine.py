"""
Subject Ranking + Priority Logic Engine for Master Scheduler AI

This engine handles ALL ranking decisions in Python — NOT by AI guessing.
OpenRouter only extracts structured info from user text.
Final ranking, scoring, and scheduling priority is computed deterministically here.

Priority Score = Exam Importance × Date Urgency × Subject Difficulty
                 × User Weakness × Revision Need × User Priority Preference
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import math
from backend.time_utils import today_ist


# ═══════════════════════════════════════════════════════════════
#  WEIGHT TABLES — Configurable scoring constants
# ═══════════════════════════════════════════════════════════════

EXAM_TYPE_WEIGHTS = {
    "competitive":  40,   # JEE, NEET, SAT, GATE, CAT, etc.
    "entrance":     40,
    "board":        35,
    "pre-board":    35,
    "university":   35,
    "semester":     35,
    "final":        30,
    "annual":       30,
    "school":       25,
    "mid-term":     20,
    "unit_test":    20,
    "class_test":   20,
    "mock":         20,
    "tuition":      10,
    "coaching":     15,
    "practice":     10,
    "self_test":    8,
    "revision":     8,
    "assignment":   12,
}

URGENCY_WEIGHTS = {
    "overdue":      35,   # Already past — highest urgency
    "tomorrow":     30,
    "within_3":     25,   # Within 3 days
    "within_7":     20,   # Within 7 days
    "within_15":    10,   # Within 15 days
    "within_30":    5,    # Within 30 days
    "far":          2,    # More than 30 days
}

DIFFICULTY_WEIGHTS = {
    "very_hard":    25,
    "hard":         20,
    "medium":       10,
    "easy":         5,
    "very_easy":    2,
}

CONFIDENCE_WEIGHTS = {
    # User confidence 1-10 → weakness score
    1: 25, 2: 22, 3: 20,
    4: 15, 5: 15,
    6: 8, 7: 8,
    8: 3, 9: 2, 10: 1,
}

REVISION_WEIGHTS = {
    "not_started":      15,
    "needs_revision":   10,
    "partially_done":   7,
    "revised_once":     5,
    "fully_revised":    2,
}

USER_PRIORITY_WEIGHTS = {
    "critical":     20,   # User says "very important" / "must score"
    "high":         15,
    "medium":       8,
    "low":          3,
    "skip_ok":      0,    # User says "comfortable already"
}


# ═══════════════════════════════════════════════════════════════
#  DEFAULT DIFFICULTY DATABASE
#  Baseline difficulty estimation for common subjects/topics.
#  NOT the final truth — user input overrides this.
# ═══════════════════════════════════════════════════════════════

DEFAULT_SUBJECT_DIFFICULTY = {
    # Maths topics
    "integration":          "hard",
    "calculus":             "hard",
    "differential_equations": "very_hard",
    "trigonometry":         "hard",
    "probability":          "medium",
    "statistics":           "medium",
    "algebra":              "medium",
    "linear_algebra":       "medium",
    "matrices":             "medium",
    "determinants":         "medium",
    "coordinate_geometry":  "medium",
    "complex_numbers":      "hard",
    "permutations":         "medium",
    "combinations":         "medium",
    "vectors":              "medium",
    "3d_geometry":          "hard",
    "sequences_series":     "medium",
    "limits":               "medium",
    "continuity":           "hard",
    "differentiability":    "hard",
    "sets":                 "easy",
    "relations":            "easy",
    "functions":            "medium",
    "binomial_theorem":     "medium",
    "mathematical_induction": "medium",

    # Physics topics
    "mechanics":            "hard",
    "thermodynamics":       "hard",
    "optics":               "medium",
    "electrostatics":       "hard",
    "current_electricity":  "medium",
    "magnetism":            "hard",
    "electromagnetic_induction": "hard",
    "waves":                "medium",
    "modern_physics":       "medium",
    "nuclear_physics":      "hard",
    "semiconductors":       "medium",
    "ray_optics":           "medium",
    "wave_optics":          "hard",
    "rotational_motion":    "very_hard",
    "fluid_mechanics":      "hard",
    "kinematics":           "medium",
    "laws_of_motion":       "medium",
    "work_energy_power":    "medium",
    "gravitation":          "medium",
    "oscillations":         "medium",

    # Chemistry topics
    "organic_chemistry":    "hard",
    "inorganic_chemistry":  "medium",
    "physical_chemistry":   "hard",
    "electrochemistry":     "hard",
    "chemical_kinetics":    "medium",
    "chemical_bonding":     "medium",
    "periodic_table":       "easy",
    "solutions":            "medium",
    "equilibrium":          "medium",
    "redox_reactions":      "medium",
    "coordination_compounds": "hard",
    "polymers":             "easy",
    "biomolecules":         "easy",
    "hydrocarbons":         "medium",
    "alcohols_phenols":     "medium",
    "aldehydes_ketones":    "hard",
    "amines":               "medium",
    "surface_chemistry":    "easy",
    "solid_state":          "medium",
    "p_block_elements":     "hard",
    "d_block_elements":     "hard",

    # Biology topics
    "genetics":             "hard",
    "evolution":            "medium",
    "ecology":              "medium",
    "cell_biology":         "medium",
    "human_physiology":     "hard",
    "plant_physiology":     "hard",
    "molecular_biology":    "hard",
    "biotechnology":        "medium",
    "reproduction":         "medium",
    "immunology":           "hard",

    # English
    "grammar":              "easy",
    "writing":              "medium",
    "comprehension":        "easy",
    "literature":           "medium",
    "poetry":               "medium",
    "essay_writing":        "medium",

    # Computer Science
    "data_structures":      "hard",
    "algorithms":           "hard",
    "databases":            "medium",
    "networking":           "medium",
    "operating_systems":    "hard",
    "programming":          "medium",
    "python":               "easy",
    "java":                 "medium",
    "sql":                  "easy",
    "web_development":      "medium",

    # General subjects (broad)
    "maths":                "hard",
    "physics":              "hard",
    "chemistry":            "medium",
    "biology":              "medium",
    "english":              "easy",
    "hindi":                "easy",
    "computer_science":     "medium",
    "history":              "medium",
    "geography":            "medium",
    "economics":            "medium",
    "political_science":    "easy",
    "sociology":            "easy",
    "psychology":           "medium",
    "accountancy":          "medium",
    "business_studies":     "easy",
}


# ═══════════════════════════════════════════════════════════════
#  EXAM TYPE DETECTION
# ═══════════════════════════════════════════════════════════════

EXAM_TYPE_KEYWORDS = {
    "competitive":  ["jee", "neet", "sat", "gre", "gate", "cat", "upsc",
                     "olympiad", "ntse", "kvpy", "clat", "aiims", "bitsat",
                     "competitive", "entrance"],
    "board":        ["board", "cbse", "icse", "isc", "state board",
                     "hsc", "ssc", "boards"],
    "pre-board":    ["pre-board", "preboard", "pre board"],
    "university":   ["university", "semester", "end sem", "endsem"],
    "final":        ["final", "annual", "yearly"],
    "school":       ["school exam", "school test", "class exam"],
    "mid-term":     ["mid-term", "midterm", "mid term", "half yearly"],
    "unit_test":    ["unit test", "chapter test", "class test"],
    "mock":         ["mock", "sample paper", "practice test", "mock test"],
    "tuition":      ["tuition", "coaching test", "institute test"],
    "assignment":   ["assignment", "project", "homework"],
}


def detect_exam_type(text: str) -> str:
    """Detect exam type from user text. Returns exam type key."""
    text_lower = text.lower()
    for exam_type, keywords in EXAM_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return exam_type
    return "school"  # Default fallback


# ═══════════════════════════════════════════════════════════════
#  DIFFICULTY DETECTION
# ═══════════════════════════════════════════════════════════════

def get_default_difficulty(topic: str) -> str:
    """
    Get baseline difficulty for a topic from the knowledge base.
    Normalizes the topic name before lookup.
    """
    normalized = topic.lower().strip()
    normalized = normalized.replace(" ", "_").replace("-", "_")
    normalized = normalized.replace("'", "").replace("'", "")

    # Direct match
    if normalized in DEFAULT_SUBJECT_DIFFICULTY:
        return DEFAULT_SUBJECT_DIFFICULTY[normalized]

    # Partial match — find best match
    for key, difficulty in DEFAULT_SUBJECT_DIFFICULTY.items():
        if key in normalized or normalized in key:
            return difficulty

    return "medium"  # Unknown topic defaults to medium


def compute_adjusted_difficulty(topic: str, user_confidence: int = None) -> str:
    """
    Compute final difficulty by combining baseline + user confidence.
    User confidence overrides baseline when significantly different.
    """
    baseline = get_default_difficulty(topic)

    if user_confidence is None:
        return baseline

    difficulty_levels = ["very_easy", "easy", "medium", "hard", "very_hard"]
    baseline_idx = difficulty_levels.index(baseline)

    # Map confidence to difficulty index (inverse — low confidence = high difficulty)
    if user_confidence <= 2:
        user_idx = 4  # very_hard
    elif user_confidence <= 4:
        user_idx = 3  # hard
    elif user_confidence <= 6:
        user_idx = 2  # medium
    elif user_confidence <= 8:
        user_idx = 1  # easy
    else:
        user_idx = 0  # very_easy

    # Weighted average: 40% baseline + 60% user (user feeling matters more)
    final_idx = round(baseline_idx * 0.4 + user_idx * 0.6)
    final_idx = max(0, min(4, final_idx))

    return difficulty_levels[final_idx]


# ═══════════════════════════════════════════════════════════════
#  URGENCY CALCULATION
# ═══════════════════════════════════════════════════════════════

def compute_urgency(exam_date_str: str, reference_date: date = None) -> Tuple[str, int]:
    """
    Calculate urgency level and days remaining.
    Returns (urgency_key, days_remaining).
    """
    if reference_date is None:
        reference_date = today_ist()

    try:
        exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return "far", 999

    days_left = (exam_date - reference_date).days

    if days_left < 0:
        return "overdue", days_left
    elif days_left <= 1:
        return "tomorrow", days_left
    elif days_left <= 3:
        return "within_3", days_left
    elif days_left <= 7:
        return "within_7", days_left
    elif days_left <= 15:
        return "within_15", days_left
    elif days_left <= 30:
        return "within_30", days_left
    else:
        return "far", days_left


# ═══════════════════════════════════════════════════════════════
#  PRIORITY SCORE CALCULATOR
# ═══════════════════════════════════════════════════════════════

class SubjectEntry:
    """Represents a single subject/topic to be ranked."""

    def __init__(
        self,
        subject: str,
        topic: str = "",
        exam_type: str = "school",
        exam_date: str = "",
        user_confidence: int = 5,
        revision_status: str = "needs_revision",
        user_priority: str = "medium",
        estimated_hours: float = 2.0,
        color: str = "#4A90D9",
    ):
        self.subject = subject
        self.topic = topic or subject
        self.exam_type = exam_type
        self.exam_date = exam_date
        self.user_confidence = max(1, min(10, user_confidence))
        self.revision_status = revision_status
        self.user_priority = user_priority
        self.estimated_hours = estimated_hours
        self.color = color

        # Computed
        self.priority_score = 0
        self.difficulty = "medium"
        self.urgency_key = "far"
        self.days_left = 999
        self.reasoning = []
        self.recommended_action = ""

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "topic": self.topic,
            "exam_type": self.exam_type,
            "exam_date": self.exam_date,
            "user_confidence": self.user_confidence,
            "revision_status": self.revision_status,
            "user_priority": self.user_priority,
            "estimated_hours": self.estimated_hours,
            "color": self.color,
            "priority_score": self.priority_score,
            "difficulty": self.difficulty,
            "urgency_key": self.urgency_key,
            "days_left": self.days_left,
            "reasoning": self.reasoning,
            "recommended_action": self.recommended_action,
        }


def compute_priority_score(entry: SubjectEntry, reference_date: date = None) -> SubjectEntry:
    """
    Compute the full priority score for a subject entry.
    Combines all weight factors into a single score (0-100 normalized).
    """
    reasons = []

    # 1. Exam Importance
    exam_weight = EXAM_TYPE_WEIGHTS.get(entry.exam_type, 20)
    reasons.append(f"Exam type '{entry.exam_type}' → +{exam_weight}")

    # 2. Date Urgency
    entry.urgency_key, entry.days_left = compute_urgency(entry.exam_date, reference_date)
    urgency_weight = URGENCY_WEIGHTS.get(entry.urgency_key, 5)
    if entry.days_left >= 0:
        reasons.append(f"{entry.days_left} days until exam → +{urgency_weight}")
    else:
        reasons.append(f"Exam overdue by {abs(entry.days_left)} day(s) → +{urgency_weight}")

    # 3. Difficulty (baseline + user adjustment)
    entry.difficulty = compute_adjusted_difficulty(entry.topic, entry.user_confidence)
    difficulty_weight = DIFFICULTY_WEIGHTS.get(entry.difficulty, 10)
    reasons.append(f"Difficulty '{entry.difficulty}' → +{difficulty_weight}")

    # 4. User Weakness (from confidence)
    weakness_weight = CONFIDENCE_WEIGHTS.get(entry.user_confidence, 8)
    reasons.append(f"Confidence {entry.user_confidence}/10 → +{weakness_weight}")

    # 5. Revision Need
    revision_weight = REVISION_WEIGHTS.get(entry.revision_status, 7)
    reasons.append(f"Revision '{entry.revision_status}' → +{revision_weight}")

    # 6. User Priority Preference
    priority_weight = USER_PRIORITY_WEIGHTS.get(entry.user_priority, 8)
    reasons.append(f"User priority '{entry.user_priority}' → +{priority_weight}")

    # ── Compute raw score ──
    raw_score = (
        exam_weight
        + urgency_weight
        + difficulty_weight
        + weakness_weight
        + revision_weight
        + priority_weight
    )

    # Maximum possible raw score = 40 + 35 + 25 + 25 + 15 + 20 = 160
    # Normalize to 0-100
    entry.priority_score = min(100, round((raw_score / 160) * 100))
    entry.reasoning = reasons

    # Generate recommended action
    entry.recommended_action = _generate_action(entry)

    return entry


def _generate_action(entry: SubjectEntry) -> str:
    """Generate a human-readable recommended action."""
    if entry.priority_score >= 80:
        return f"🔴 HIGH PRIORITY: Focus on {entry.topic} immediately. Allocate maximum study time."
    elif entry.priority_score >= 60:
        return f"🟡 IMPORTANT: Study {entry.topic} regularly. Schedule dedicated sessions."
    elif entry.priority_score >= 40:
        return f"🟢 MODERATE: Include {entry.topic} in your study plan with standard time."
    elif entry.priority_score >= 20:
        return f"🔵 LOW: {entry.topic} can be studied with lighter focus. Quick revision may suffice."
    else:
        return f"⚪ OPTIONAL: {entry.topic} is low priority. Can be deferred if time is tight."


# ═══════════════════════════════════════════════════════════════
#  RANKING ENGINE — Main API
# ═══════════════════════════════════════════════════════════════

def rank_subjects(entries: List[SubjectEntry], reference_date: date = None) -> Dict:
    """
    Main ranking function. Takes a list of subjects and returns
    ranked results with scores, reasoning, and recommendations.
    """
    if reference_date is None:
        reference_date = today_ist()

    # Compute scores for all entries
    for entry in entries:
        compute_priority_score(entry, reference_date)

    # Sort by priority score (highest first)
    ranked = sorted(entries, key=lambda e: e.priority_score, reverse=True)

    # Build ranked output
    ranked_list = []
    for rank, entry in enumerate(ranked, 1):
        ranked_list.append({
            "rank": rank,
            **entry.to_dict()
        })

    # Generate overall recommendation
    top_3 = ranked[:3]
    focus_order = [e.topic for e in top_3]

    # Identify crunch candidates (things to reduce in time crunch)
    crunch_reduce = [e.topic for e in ranked if e.priority_score < 30]
    crunch_protect = [e.topic for e in ranked if e.priority_score >= 70]

    return {
        "ranked_subjects": ranked_list,
        "focus_order": focus_order,
        "time_crunch": {
            "protect": crunch_protect,
            "can_reduce": crunch_reduce,
            "message": _crunch_message(crunch_protect, crunch_reduce)
        },
        "summary": _generate_summary(ranked),
        "total_estimated_hours": sum(e.estimated_hours for e in ranked),
    }


def _crunch_message(protect: List[str], reduce: List[str]) -> str:
    """Generate time-crunch advice message."""
    parts = []
    if protect:
        parts.append(f"🛡️ Protect: {', '.join(protect)}")
    if reduce:
        parts.append(f"✂️ Can reduce: {', '.join(reduce)}")
    if not protect and not reduce:
        return "All tasks have moderate priority. Distribute time evenly."
    return " | ".join(parts)


def _generate_summary(ranked: List[SubjectEntry]) -> str:
    """Generate a natural language summary of the ranking."""
    if not ranked:
        return "No subjects to rank."

    top = ranked[0]
    lines = [
        f"📊 **Priority Ranking Complete**",
        f"",
        f"**Top Priority**: {top.topic} (Score: {top.priority_score}/100)",
    ]

    if top.priority_score >= 70:
        lines.append(f"⚡ This needs immediate attention!")

    if len(ranked) > 1:
        lines.append(f"")
        lines.append(f"**Study Order**:")
        for i, entry in enumerate(ranked[:5], 1):
            emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][i - 1] if i <= 5 else f"{i}."
            lines.append(f"{emoji} {entry.topic} — Score {entry.priority_score}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  MISSED DAY RE-RANKING
# ═══════════════════════════════════════════════════════════════

def rerank_after_missed_day(
    entries: List[SubjectEntry],
    missed_topics: List[str],
    available_hours: float,
    reference_date: date = None
) -> Dict:
    """
    Re-rank subjects after user misses a study day.
    Marks missed topics for higher urgency and generates recovery options.
    """
    if reference_date is None:
        reference_date = today_ist()

    # Boost missed topics' urgency
    for entry in entries:
        if entry.topic in missed_topics or entry.subject in missed_topics:
            # Move revision status to "not_started" if it was pending
            if entry.revision_status in ("needs_revision", "partially_done"):
                entry.revision_status = "not_started"

    # Re-rank with updated data
    result = rank_subjects(entries, reference_date)

    # Calculate total missed hours
    missed_entries = [e for e in entries if e.topic in missed_topics or e.subject in missed_topics]
    missed_hours = sum(e.estimated_hours for e in missed_entries)

    # Generate recovery options
    recovery_options = []

    # Option A: Shift forward
    recovery_options.append({
        "id": "A",
        "label": "Shift schedule forward",
        "description": f"Move all remaining tasks forward by {missed_hours:.1f} hours. "
                       "Safest option but extends your timeline.",
        "impact": "low_risk"
    })

    # Option B: Compress
    if available_hours > 0:
        extra_per_day = round(missed_hours / max(1, 3), 1)  # Spread over 3 days
        recovery_options.append({
            "id": "B",
            "label": "Compress remaining schedule",
            "description": f"Add ~{extra_per_day} extra hours/day for the next 3 days to catch up.",
            "impact": "medium_risk"
        })

    # Option C: Skip low-priority
    low_priority = [e for e in entries if e.priority_score < 30]
    if low_priority:
        recovery_options.append({
            "id": "C",
            "label": "Skip low-priority tasks",
            "description": f"Drop {len(low_priority)} lower-priority tasks: "
                           f"{', '.join(e.topic for e in low_priority[:3])}",
            "impact": "medium_risk"
        })

    # Option D: Focus critical only
    critical = [e for e in entries if e.priority_score >= 70]
    if critical:
        recovery_options.append({
            "id": "D",
            "label": "Focus only on critical exams",
            "description": f"Focus all time on {len(critical)} high-priority items: "
                           f"{', '.join(e.topic for e in critical[:3])}. Best for severe time crunch.",
            "impact": "high_risk"
        })

    result["recovery"] = {
        "missed_topics": missed_topics,
        "missed_hours": missed_hours,
        "options": recovery_options,
    }

    return result


# ═══════════════════════════════════════════════════════════════
#  SMART STUDY ORDER GENERATOR
#  Given ranked subjects + available time, produce an optimized
#  study order for a single day.
# ═══════════════════════════════════════════════════════════════

def generate_daily_study_order(
    entries: List[SubjectEntry],
    available_hours: float,
    reference_date: date = None,
    time_of_day: str = "mixed"   # "morning", "evening", "night", "mixed"
) -> List[Dict]:
    """
    Generate an optimized study order for a single day.
    Allocates time proportionally to priority scores.
    """
    if reference_date is None:
        reference_date = today_ist()

    # Rank first
    for entry in entries:
        compute_priority_score(entry, reference_date)

    ranked = sorted(entries, key=lambda e: e.priority_score, reverse=True)

    # Filter to subjects that need work
    active = [e for e in ranked if e.priority_score > 5]
    if not active:
        return []

    # Allocate time proportionally to priority score
    total_score = sum(e.priority_score for e in active)
    available_minutes = available_hours * 60

    study_order = []
    remaining_minutes = available_minutes

    for entry in active:
        if remaining_minutes <= 0:
            break

        # Proportional allocation
        proportion = entry.priority_score / max(total_score, 1)
        allocated = round(proportion * available_minutes)

        # Minimum 15 minutes, maximum = estimated hours or remaining
        allocated = max(15, min(allocated, entry.estimated_hours * 60, remaining_minutes))

        study_order.append({
            "subject": entry.subject,
            "topic": entry.topic,
            "color": entry.color,
            "allocated_minutes": allocated,
            "priority_score": entry.priority_score,
            "difficulty": entry.difficulty,
            "reason": entry.recommended_action,
        })

        remaining_minutes -= allocated

    return study_order


# ═══════════════════════════════════════════════════════════════
#  HELPER: Parse ranking data from AI-extracted info
# ═══════════════════════════════════════════════════════════════

def parse_subjects_from_ai_data(ai_extracted: Dict) -> List[SubjectEntry]:
    """
    Convert AI-extracted structured data into SubjectEntry objects.
    The AI extracts: subjects, topics, exam_dates, confidence levels, etc.
    This function turns that into rankable entries.
    """
    entries = []
    subjects = ai_extracted.get("subjects", [])

    for subj in subjects:
        exam_type = detect_exam_type(
            subj.get("exam_description", "") or subj.get("subject", "")
        )

        entry = SubjectEntry(
            subject=subj.get("subject", "Unknown"),
            topic=subj.get("topic", subj.get("subject", "Unknown")),
            exam_type=exam_type,
            exam_date=subj.get("exam_date", ""),
            user_confidence=subj.get("confidence", 5),
            revision_status=subj.get("revision_status", "needs_revision"),
            user_priority=subj.get("priority", "medium"),
            estimated_hours=subj.get("estimated_hours", 2.0),
            color=subj.get("color", "#4A90D9"),
        )
        entries.append(entry)

    return entries


# ═══════════════════════════════════════════════════════════════
#  SUBJECT COLOR PALETTE (consistent assignment)
# ═══════════════════════════════════════════════════════════════

SUBJECT_COLORS = {
    "maths":            "#4A90D9",
    "mathematics":      "#4A90D9",
    "physics":          "#10B981",
    "chemistry":        "#F59E0B",
    "biology":          "#EC4899",
    "english":          "#8B5CF6",
    "hindi":            "#D97706",
    "computer science": "#06B6D4",
    "history":          "#D97706",
    "geography":        "#059669",
    "economics":        "#7C3AED",
    "accountancy":      "#2563EB",
    "business studies": "#0891B2",
    "political science": "#DC2626",
    "sociology":        "#9333EA",
    "psychology":       "#E11D48",
    "break":            "#9CA3AF",
    "revision":         "#A855F7",
    "mock_test":        "#EF4444",
    "exam":             "#EF4444",
}

# Extended palette for unknown subjects
EXTENDED_COLORS = [
    "#4A90D9", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899",
    "#06B6D4", "#D97706", "#059669", "#7C3AED", "#2563EB",
    "#0891B2", "#DC2626", "#9333EA", "#E11D48", "#0D9488",
    "#7C2D12", "#4338CA", "#BE123C", "#15803D", "#B45309",
]

_color_assignment_counter = 0


def get_subject_color(subject: str) -> str:
    """Get a consistent color for a subject."""
    global _color_assignment_counter
    normalized = subject.lower().strip()

    if normalized in SUBJECT_COLORS:
        return SUBJECT_COLORS[normalized]

    # Partial match
    for key, color in SUBJECT_COLORS.items():
        if key in normalized or normalized in key:
            return color

    # Assign from extended palette
    idx = _color_assignment_counter % len(EXTENDED_COLORS)
    color = EXTENDED_COLORS[idx]
    SUBJECT_COLORS[normalized] = color
    _color_assignment_counter += 1
    return color
