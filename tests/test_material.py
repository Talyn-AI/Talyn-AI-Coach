"""Document analysis and schedule generation (mock mode).

The fake answers from markers in the user message, so the document text used
here must avoid every trigger phrase in the fake's marker table (quiz,
study plan, revision, ...). Bland filler is a feature, not laziness: a
"realistic" document mentioning quizzes would route to the quiz builder.
"""
from app.models.schemas import DifficultyLevel, LearnerContext
from app.services import material_service

DOC = (
    "Photosynthesis converts light energy into chemical energy. Chlorophyll "
    "absorbs red and blue wavelengths. The Calvin cycle fixes carbon dioxide "
    "into sugar using ATP and NADPH from the light reactions. Stomata regulate "
    "gas exchange and water loss in leaves."
)


def _learner() -> LearnerContext:
    return LearnerContext(
        learner_name="Amina",
        learner_id="learner_001",
        current_course="Biology",
        current_lesson="Plant processes",
        current_topic="Photosynthesis",
        interests=["design"],
        difficulty_level=DifficultyLevel.BEGINNER,
        xp_total=10,
        xp_this_week=10,
        streak_days=1,
        lessons_completed=1,
        lessons_total=4,
        completion_percent=25.0,
    )


def test_analyze_returns_a_shaped_preview():
    result = material_service.analyze_material(DOC * 4, "photosynthesis.pdf")
    assert len(result.topics) >= 1
    assert len(result.objectives) >= 1
    assert result.estimated_minutes > 0
    assert len(result.summary) > 20


def test_generate_schedule_returns_fourteen_days_by_default():
    result = material_service.generate_schedule(
        DOC * 4, ["Photosynthesis"], ["Explain the process"], 14, "beginner"
    )
    assert result.title
    assert len(result.days) == 14
    assert [d.day for d in result.days] == list(range(1, 15))
    for day in result.days:
        assert day.title
        assert len(day.objectives) >= 1
        assert len(day.tasks) >= 1


def test_generate_schedule_honours_the_day_count():
    result = material_service.generate_schedule(
        DOC * 4, ["T"], ["O"], 5, "beginner"
    )
    assert len(result.days) == 5


def test_generate_schedule_ends_with_review_not_new_material():
    result = material_service.generate_schedule(
        DOC * 4, ["T"], ["O"], 14, "beginner"
    )
    tail = " ".join(
        d.title + " " + " ".join(d.tasks) for d in result.days[-2:]
    ).lower()
    assert "review" in tail or "self-test" in tail or "recap" in tail


def test_empty_schedule_payload_is_rejected(monkeypatch):
    """The backend stores whatever this returns, so a day-less schedule must
    fail here rather than create an empty plan that reads as complete."""
    import pytest

    from app.services import material_service as ms

    monkeypatch.setattr(
        ms, "_call_claude", lambda *a, **k: '{"title": "Nothing", "days": []}'
    )
    with pytest.raises(ValueError):
        ms.generate_schedule(DOC * 4, ["T"], ["O"], 14, "beginner")


def test_purpose_shapes_the_prompt():
    from app.prompts.material_prompts import generate_schedule_prompt

    _, with_goal = generate_schedule_prompt(
        DOC, ["T"], ["O"], 2, "beginner", "final exam"
    )
    _, without_goal = generate_schedule_prompt(
        DOC, ["T"], ["O"], 2, "beginner", ""
    )
    assert "final exam" in with_goal[0]["content"]
    assert "final exam" not in without_goal[0]["content"]
    assert "durable understanding" in without_goal[0]["content"]


def test_purpose_reaches_generation(monkeypatch):
    from app.services import material_service as ms

    seen = {}

    def _capture(system, messages, max_tokens):
        seen["messages"] = messages
        return (
            '{"title": "Exam plan", "days": ['
            '{"day": 1, "title": "D1", "objectives": ["O"], "tasks": ["T"]},'
            '{"day": 2, "title": "D2", "objectives": ["O"], "tasks": ["T"]}]}'
        )

    monkeypatch.setattr(ms, "_call_claude", _capture)
    result = ms.generate_schedule(DOC * 4, ["T"], ["O"], 2, "beginner",
                                  "entrance exam")
    assert result.title == "Exam plan"
    assert len(result.days) == 2
