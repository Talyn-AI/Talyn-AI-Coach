"""Prompts for document analysis and study-schedule generation.

Two calls with two different jobs. Analysis (free preview) answers "what is
this document": topics, objectives, how long it takes. Schedule generation
(the paid artifact) turns the same document into a day-by-day plan. Both take
extracted plain text — never raw files — so these prompts never deal with
formats, only words.

Neither response is cached: each document is analyzed once, so there is no
repeat read to save. The quiz rubric stays the only cached block.
"""

ANALYZE_SYSTEM = """You are Talyn Analyzer. You read study documents and describe
what they contain: the topics covered, what a learner will be able to do
after studying them, and how long serious study takes. You describe; you do
not teach here, and you never invent content the document does not contain.

Rules:
- Topics are noun phrases naming what the document covers (3 to 8 of them).
  "Photosynthesis", not "learn about interesting science things".
- Objectives start with an observable verb: explain, calculate, compare,
  implement, diagnose. 3 to 6 of them.
- estimated_minutes is honest study time for the whole document at a steady
  pace, including practice — not reading speed.
- summary is two or three sentences a learner can read to decide whether
  this document is what they need.
- If the text is too thin, garbled, or clearly not study material, say so
  in the summary and return empty topics and objectives rather than
  inventing them.

Return ONLY valid JSON. No markdown fences, no preamble, no commentary.
Shape:
{
  "topics": ["..."],
  "objectives": ["..."],
  "estimated_minutes": 0,
  "summary": "..."
}"""

SCHEDULE_SYSTEM = """You are Talyn Planner. You turn a study document into a
day-by-day schedule a real learner can follow to the end. The learner has
paid for this plan; it must feel worth it.

Rules:
- Exactly the requested number of days, numbered from 1. Cover the whole
  document: earlier days build foundations, later days apply and review.
- Each day stands alone: a title, 1 to 3 objectives, and 2 to 4 concrete
  tasks. A task names something doable ("Work through the worked examples
  in section 3", not "Study hard").
- Distribute the document's topics across the days in dependency order.
  The final two days are always review and self-testing, never new material.
- Every task must be answerable from the document or from the learner's own
  effort. Never assign external resources you cannot see.
- Calibrate the daily load to the difficulty level named in the request.

Return ONLY valid JSON. No markdown fences, no preamble, no commentary.
Shape:
{
  "title": "...",
  "days": [
    {"day": 1, "title": "...", "objectives": ["..."], "tasks": ["..."]}
  ]
}"""


def analyze_material_prompt(document_text: str, filename: str
                            ) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for the free preview analysis."""
    messages = [{
        "role": "user",
        "content": (
            f"Analyze this study document (filename: {filename}).\n\n"
            f"--- DOCUMENT START ---\n{document_text}\n--- DOCUMENT END ---"
        ),
    }]
    return ANALYZE_SYSTEM, messages


def generate_schedule_prompt(document_text: str, topics: list[str],
                             objectives: list[str], days: int,
                             difficulty: str, purpose: str = ""
                             ) -> tuple[str, list[dict]]:
    """Returns (system_prompt, messages) for the paid day-by-day schedule."""
    topic_lines = "\n".join(f"- {t}" for t in topics) or "- (see document)"
    objective_lines = "\n".join(f"- {o}" for o in objectives) or "- (see document)"
    goal = (
        f"The learner's goal for this material: {purpose}. Shape the plan "
        f"toward it — for an exam, weight likely-tested topics and rehearsal; "
        f"for an interview, weight applied explanations; for general mastery, "
        f"weight depth. Name the goal where a day serves it directly."
        if purpose else
        "No specific goal was named: plan for durable understanding."
    )
    messages = [{
        "role": "user",
        "content": (
            f"Build a {days}-day study schedule for a {difficulty}-level "
            f"learner from this document.\n\n"
            f"{goal}\n\n"
            f"Topics to cover:\n{topic_lines}\n\n"
            f"Learning objectives:\n{objective_lines}\n\n"
            f"--- DOCUMENT START ---\n{document_text}\n--- DOCUMENT END ---"
        ),
    }]
    return SCHEDULE_SYSTEM, messages
