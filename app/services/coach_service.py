"""
Talyn AI Coach â€” Claude API Service

Thin wrapper around the Anthropic SDK. All prompt construction
lives in app/prompts/coach_prompts.py â€” this module only handles
the API call and error handling.
"""

import json
import os
import anthropic
from app.models.schemas import (
    LearnerContext, CoachAction, CoachResponse, QuizResponse, QuizQuestion,
    CourseQaResponse,
)
from app.prompts.coach_prompts import (
    answer_question_prompt,
    explain_concept_prompt,
    create_study_plan_prompt,
    encourage_prompt,
    generate_quiz_prompt,
    grounded_qa_prompt,
    QUIZ_RUBRIC,
)

# Initialise client once at import time (reads ANTHROPIC_API_KEY from env)
_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "mock-key"))

MODEL   = "claude-sonnet-5-5"
MAX_TOKENS = 1500


# â”€â”€ Internal helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _call_claude(system: str, messages: list[dict], max_tokens: int = MAX_TOKENS,
                cached_blocks: list[str] | None = None) -> str:
    """Make a synchronous call to Claude and return the text response.

    `cached_blocks` are stable instruction blocks (identical on every call)
    sent ahead of `system` with a cache breakpoint. Repeat reads of a cached
    prefix are billed at the cache-read rate instead of the full input rate,
    but only when the prefix is long enough (about 1024 tokens on Sonnet)
    and byte-identical — per-learner text must never go in one. When empty,
    the call is byte-for-byte what it was before caching existed.
    """
    if cached_blocks:
        system_param: str | list[dict] = [
            {"type": "text", "text": block,
             "cache_control": {"type": "ephemeral"}}
            for block in cached_blocks
        ] + [{"type": "text", "text": system}]
    else:
        system_param = system
    response = _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system_param,
        messages=messages,
    )
    return response.content[0].text


# â”€â”€ Public service functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def answer_question(learner: LearnerContext, question: str) -> CoachResponse:
    system, messages = answer_question_prompt(learner, question)
    text = _call_claude(system, messages)
    return CoachResponse(
        action=CoachAction.ANSWER_QUESTION,
        learner_id=learner.learner_id,
        response=text,
    )


def answer_from_course(learner: LearnerContext, course_title: str,
                       content: str, question: str) -> CourseQaResponse:
    """Answer strictly from the supplied lesson text. The content arrives
    inline because the coach never touches the database."""
    system, messages = grounded_qa_prompt(learner, course_title, content,
                                          question)
    return CourseQaResponse(
        answer=_call_claude(system, messages, max_tokens=1000))


def explain_concept(learner: LearnerContext, concept: str) -> CoachResponse:
    system, messages = explain_concept_prompt(learner, concept)
    text = _call_claude(system, messages)
    return CoachResponse(
        action=CoachAction.EXPLAIN_CONCEPT,
        learner_id=learner.learner_id,
        response=text,
    )


def create_study_plan(learner: LearnerContext, goals: str) -> CoachResponse:
    system, messages = create_study_plan_prompt(learner, goals)
    text = _call_claude(system, messages, max_tokens=2000)
    return CoachResponse(
        action=CoachAction.CREATE_STUDY_PLAN,
        learner_id=learner.learner_id,
        response=text,
    )


def encourage(learner: LearnerContext, trigger: str) -> CoachResponse:
    system, messages = encourage_prompt(learner, trigger)
    text = _call_claude(system, messages, max_tokens=300)
    return CoachResponse(
        action=CoachAction.ENCOURAGE,
        learner_id=learner.learner_id,
        response=text,
    )


def generate_quiz(learner: LearnerContext, topic: str, num_questions: int) -> QuizResponse:
    system, messages = generate_quiz_prompt(learner, topic, num_questions)
    raw = _call_claude(system, messages, max_tokens=2000,
                       cached_blocks=[QUIZ_RUBRIC])

    # Strip markdown fences if Claude wraps the JSON despite instructions
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    data = json.loads(clean)
    questions = [QuizQuestion(**q) for q in data["questions"]]

    return QuizResponse(
        learner_id=learner.learner_id,
        topic=topic,
        questions=questions,
    )
