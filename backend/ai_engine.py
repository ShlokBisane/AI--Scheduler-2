"""
AI Engine — OpenRouter API only.
Robust schedule JSON extraction that never shows raw code to users.
"""

import json
import re
import requests
from typing import Generator, List, Dict, Optional
from backend.prompts import build_student_prompt, build_teacher_prompt, CHAT_TITLE_PROMPT


# ─── OpenRouter API ─────────────────────────────────────────

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def chat_openrouter(api_key: str, messages: List[Dict], model: str = "openai/gpt-4o-mini") -> str:
    """Send chat to OpenRouter API and return full response."""
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Master Scheduler AI"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def stream_openrouter(api_key: str, messages: List[Dict], model: str = "openai/gpt-4o-mini") -> Generator[str, None, None]:
    """Stream chat response from OpenRouter API."""
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Master Scheduler AI"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "stream": True
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
    resp.raise_for_status()
    
    for line in resp.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
            except json.JSONDecodeError:
                continue


# ─── Unified Interface ──────────────────────────────────────

def build_messages(chat_messages: List[Dict], mode: str = "student",
                   profile: dict = None, calendar_context: str = "") -> List[Dict]:
    """Build message list with system prompt for API call."""
    if mode == "teacher":
        system_prompt = build_teacher_prompt(profile)
    else:
        system_prompt = build_student_prompt(profile)

    if calendar_context:
        system_prompt += calendar_context
    
    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in chat_messages:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    return messages


def get_ai_response(api_key: str, messages: List[Dict],
                    mode: str = "student", profile: dict = None,
                    calendar_context: str = "") -> str:
    """Get full AI response using OpenRouter."""
    formatted = build_messages(messages, mode, profile, calendar_context)
    return chat_openrouter(api_key, formatted)


def stream_ai_response(api_key: str, messages: List[Dict],
                       mode: str = "student", profile: dict = None,
                       calendar_context: str = "") -> Generator[str, None, None]:
    """Stream AI response using OpenRouter."""
    formatted = build_messages(messages, mode, profile, calendar_context)
    yield from stream_openrouter(api_key, formatted)


def generate_chat_title(api_key: str, first_message: str) -> str:
    """Generate a short chat title based on the first message."""
    messages = [
        {"role": "system", "content": CHAT_TITLE_PROMPT},
        {"role": "user", "content": first_message}
    ]
    
    try:
        title = chat_openrouter(api_key, messages)
        # Clean up
        title = title.strip().strip('"').strip("'")
        if len(title) > 50:
            title = title[:47] + "..."
        return title
    except Exception:
        # Fallback: use first few words
        words = first_message.split()[:5]
        return " ".join(words)


# ─── Robust Schedule Extraction ─────────────────────────────

def extract_schedule_from_response(response_text: str) -> Optional[Dict]:
    """
    Extract schedule JSON from AI response. Tries multiple patterns:
    1. ```schedule ... ```
    2. ```json ... ``` (if contains "sessions" key)
    3. Any bare JSON block with "sessions" key
    """
    if not response_text:
        return None
    
    # Pattern 1: ```schedule block (case-insensitive)
    pattern1 = r'```[Ss]chedule\s*\n(.*?)\n```'
    match = re.search(pattern1, response_text, re.DOTALL)
    if match:
        result = _try_parse_schedule(match.group(1))
        if result:
            return result
    
    # Pattern 2: ```json block containing "sessions"
    pattern2 = r'```(?:json|JSON)?\s*\n(.*?)\n```'
    for match in re.finditer(pattern2, response_text, re.DOTALL):
        text = match.group(1)
        if '"sessions"' in text:
            result = _try_parse_schedule(text)
            if result:
                return result
    
    # Pattern 3: Any {..."sessions":...} JSON block in the text
    pattern3 = r'\{[^{}]*"sessions"\s*:\s*\[.*?\]\s*\}'
    match = re.search(pattern3, response_text, re.DOTALL)
    if match:
        result = _try_parse_schedule(match.group(0))
        if result:
            return result
    
    # Pattern 4: Deeply nested — find opening { before "sessions" and match braces
    if '"sessions"' in response_text:
        idx = response_text.find('"sessions"')
        # Walk backward to find opening {
        start = response_text.rfind('{', 0, idx)
        if start >= 0:
            # Walk forward to find matching }
            depth = 0
            for i in range(start, len(response_text)):
                if response_text[i] == '{':
                    depth += 1
                elif response_text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        result = _try_parse_schedule(response_text[start:i+1])
                        if result:
                            return result
                        break
    
    return None


def _try_parse_schedule(json_text: str) -> Optional[Dict]:
    """Try to parse a JSON string as a schedule. Returns None on failure."""
    try:
        # Clean up common issues
        cleaned = json_text.strip()
        # Remove trailing commas before } or ]
        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
        
        data = json.loads(cleaned)
        
        # Validate: must have "sessions" key with a list
        if isinstance(data, dict) and "sessions" in data and isinstance(data["sessions"], list):
            # Validate sessions have required fields
            valid_sessions = []
            for s in data["sessions"]:
                if isinstance(s, dict) and "subject" in s:
                    # Ensure all required fields exist with defaults
                    valid_sessions.append({
                        "subject": s.get("subject", "Unknown"),
                        "color": s.get("color", "#4A90D9"),
                        "date": s.get("date", ""),
                        "start_time": s.get("start_time", ""),
                        "end_time": s.get("end_time", ""),
                        "type": s.get("type", "study"),
                        "topic": s.get("topic", s.get("subject", "")),
                        "priority": s.get("priority", 3),
                    })
            
            if valid_sessions:
                data["sessions"] = valid_sessions
                return data
        
        return None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def clean_response_text(response_text: str) -> str:
    """
    Remove ALL schedule/code blocks from response text for display.
    The user should never see raw JSON in chat.
    """
    if not response_text:
        return ""
    
    cleaned = response_text
    
    # Remove ```schedule ... ``` blocks (case-insensitive)
    cleaned = re.sub(r'```[Ss]chedule\s*\n.*?\n```', '', cleaned, flags=re.DOTALL)
    
    # Remove ```json blocks that contain "sessions"
    def remove_json_schedule_blocks(text):
        result = text
        for match in re.finditer(r'```(?:json|JSON)?\s*\n(.*?)\n```', text, re.DOTALL):
            if '"sessions"' in match.group(1):
                result = result.replace(match.group(0), '')
        return result
    
    cleaned = remove_json_schedule_blocks(cleaned)
    
    # Remove any remaining bare JSON with "sessions" that's clearly schedule data
    cleaned = re.sub(r'\{[^{}]*"sessions"\s*:\s*\[.*?\]\s*\}', '', cleaned, flags=re.DOTALL)
    
    # Clean up excessive whitespace/newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned.strip()


def strip_schedule_from_streaming(text: str) -> str:
    """
    Strip schedule JSON blocks from text during streaming.
    This ensures the user NEVER sees raw code/JSON in the chat.
    Used on the frontend side as well, but backend can pre-clean too.
    """
    # Remove complete ```schedule...``` blocks
    cleaned = re.sub(r'```[Ss]chedule\s*\n.*?\n```', '', text, flags=re.DOTALL)
    
    # Remove complete ```json blocks with "sessions"
    def remove_json_blocks(t):
        result = t
        for match in re.finditer(r'```(?:json|JSON)?\s*\n(.*?)\n```', t, re.DOTALL):
            if '"sessions"' in match.group(1):
                result = result.replace(match.group(0), '')
        return result
    
    cleaned = remove_json_blocks(cleaned)
    
    # Remove partial schedule blocks that are still streaming
    # If we see ```schedule or ```json{ followed by "sessions", hide everything after
    partial_pattern = r'```[Ss]chedule\s*\n.*$'
    cleaned = re.sub(partial_pattern, '', cleaned, flags=re.DOTALL)
    
    partial_json = r'```(?:json|JSON)?\s*\n\s*\{[^}]*"sessions".*$'
    cleaned = re.sub(partial_json, '', cleaned, flags=re.DOTALL)
    
    return cleaned.strip()
