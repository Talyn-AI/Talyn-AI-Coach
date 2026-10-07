"""Material service: document analysis (free preview) and schedule generation.

Thin wrapper around the Anthropic SDK, following the per-service convention:
own client, own MODEL, own _call_claude. All prompt construction lives in
app/prompts/material_prompts.py — this module only handles the API call,
the JSON recovery, and validation of the shape the backend will store.
"""

import json
import os
import anthropic
from app.models.schemas import (
    MaterialAnalysisResponse,
    ScheduleDayOut,
    StudyScheduleResponse,
)
from app.prompts.material_prompts import (
    analyze_material_prompt,
    generate_schedule_prompt,
)

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "mock-key"))

MODEL = "claude-sonnet-5-5"
ANALYZE_MAX_TOKENS = 1500
SCHEDULE_MAX_TOKENS = 4000


def _call_claude(system: str, messages: list[dict], max_tokens: int) -> str:
    """Make a synchronous call to Claude and return the text response."""
    response = _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _clean_json(raw: str) -> dict:
    """Parse the model's reply, tolerating markdown fences around the JSON."""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())


def analyze_material(document_text: str, filename: str) -> MaterialAnalysisResponse:
    """Describe a document: topics, objectives, study time. The free preview."""
    system, messages = analyze_material_prompt(document_text, filename)
    data = _clean_json(_call_claude(system, messages, ANALYZE_MAX_TOKENS))
    return MaterialAnalysisResponse(
        topics=[str(t) for t in data.get("topics", [])][:12],
        objectives=[str(o) for o in data.get("objectives", [])][:12],
        estimated_minutes=int(data.get("estimated_minutes", 0) or 0),
        summary=str(data.get("summary", ""))[:2000],
    )


def generate_schedule(document_text: str, topics: list[str],
                      objectives: list[str], days: int,
                      difficulty: str, purpose: str = "") -> StudyScheduleResponse:
    """Build the paid day-by-day plan. Raises ValueError when the shape is
    wrong — the backend treats that as a failed generation, not content."""
    system, messages = generate_schedule_prompt(
        document_text, topics, objectives, days, difficulty, purpose
    )
    data = _clean_json(_call_claude(system, messages, SCHEDULE_MAX_TOKENS))
    title = str(data.get("title", "") or "Study schedule")[:255]
    raw_days = data.get("days", [])
    if not isinstance(raw_days, list) or not raw_days:
        raise ValueError("Schedule generation returned no days")
    out = []
    for n, raw in enumerate(raw_days[:days], start=1):
        if not isinstance(raw, dict):
            continue
        out.append(ScheduleDayOut(
            day=int(raw.get("day", n) or n),
            title=str(raw.get("title", "") or f"Day {n}")[:255],
            objectives=[str(o) for o in raw.get("objectives", [])][:8],
            tasks=[str(t) for t in raw.get("tasks", [])][:12],
        ))
    if not out:
        raise ValueError("Schedule generation returned no usable days")
    return StudyScheduleResponse(title=title, days=out)
