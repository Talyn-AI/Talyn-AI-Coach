"""Prompt caching on the quiz path.

Caching saves money only when the cached prefix is byte-identical across
requests and long enough (about 1024 tokens on Sonnet). These tests pin both
properties of the rubric plus the wire shape, so a well-meaning edit that
interpolates a name into the rubric or shrinks it below the minimum fails
here instead of silently unbilled in production.
"""
from types import SimpleNamespace

from app.models.schemas import DifficultyLevel, LearnerContext
from app.prompts.coach_prompts import QUIZ_RUBRIC, generate_quiz_prompt
from app.services import coach_service


def _learner(name: str, learner_id: str, topic: str) -> LearnerContext:
    return LearnerContext(
        learner_name=name,
        learner_id=learner_id,
        current_course="UI/UX Design Fundamentals",
        current_lesson="Lesson 4: Layout & Spacing",
        current_topic=topic,
        interests=["football", "music"],
        difficulty_level=DifficultyLevel.BEGINNER,
        xp_total=320,
        xp_this_week=85,
        streak_days=4,
        lessons_completed=6,
        lessons_total=20,
        completion_percent=30.0,
    )


def _recording_client(seen: dict):
    """Stand-in for the Anthropic client that captures the call and answers
    through the fake, so wire-shape assertions and end-to-end behaviour share
    one path."""

    from app.fake_anthropic import FakeAnthropic

    fake = FakeAnthropic()

    class Recorder:
        def __init__(self):
            self.messages = SimpleNamespace(create=self.create)

        def create(self, **kwargs):
            seen.update(kwargs)
            return fake._create(**kwargs)

    return Recorder()


def _cached_first_block(learner: LearnerContext) -> str:
    """The exact bytes that would go under the cache breakpoint."""
    seen: dict = {}
    original = coach_service._client
    coach_service._client = _recording_client(seen)
    try:
        coach_service.generate_quiz(learner, "Flexbox", 2)
    finally:
        coach_service._client = original
    return seen["system"][0]["text"]


def test_cached_prefix_is_byte_identical_across_learners_and_topics():
    """The cache invariant, measured at the wire: two different learners,
    two different topics, identical cached bytes — or no cache hit."""
    a = _cached_first_block(_learner("Adeola", "l1", "Flexbox"))
    b = _cached_first_block(_learner("Tunde", "l2", "Grid"))
    assert a == b == QUIZ_RUBRIC


def test_rubric_clears_the_cache_minimum():
    """Below the minimum Sonnet silently does not cache: tagging would be
    decoration. The Sonnet 5.5 minimum is 512 tokens; this pins 1024 so the
    rough chars-per-token estimate has room to be wrong in either direction.
    Estimated at ~4 chars per token."""
    assert len(QUIZ_RUBRIC) // 4 >= 1024, (
        f"rubric is ~{len(QUIZ_RUBRIC) // 4} tokens: "
        "too close to the cache minimum, caching may do nothing"
    )


def test_dynamic_system_still_carries_the_learner():
    """The split must not lose personalization: the dynamic block still
    names the learner and their interests."""
    system, _ = generate_quiz_prompt(_learner("Adeola", "l1", "Flexbox"), "Flexbox", 3)
    assert "Adeola" in system
    assert "football" in system


def test_quiz_user_message_keeps_the_fake_markers():
    """The mock quiz builder keys on the marker phrase and topic in the user
    message — the slimmed message must still carry both."""
    _, messages = generate_quiz_prompt(_learner("A", "l1", "T"), "CSS Flexbox", 3)
    content = messages[0]["content"]
    assert "-question multiple choice quiz" in content
    assert "quiz on 'CSS Flexbox'" in content


def test_cached_block_goes_out_with_a_breakpoint_and_system_does_not():
    """Wire shape: exactly one cache_control, on the rubric, never on the
    per-learner system block (which differs every call and could never hit)."""
    seen: dict = {}
    original = coach_service._client
    coach_service._client = _recording_client(seen)
    try:
        coach_service.generate_quiz(_learner("Adeola", "l1", "Flexbox"), "Flexbox", 2)
    finally:
        coach_service._client = original

    system = seen["system"]
    assert isinstance(system, list) and len(system) == 2
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert system[0]["text"] == QUIZ_RUBRIC
    assert "cache_control" not in system[1]
    assert "Adeola" in system[1]["text"]


def test_uncached_calls_keep_the_old_wire_shape():
    """Every other action passes no cached blocks: the request must be
    byte-for-byte what it was before caching existed (a plain string)."""
    seen: dict = {}
    original = coach_service._client
    coach_service._client = _recording_client(seen)
    try:
        coach_service.encourage(_learner("A", "l1", "T"), "completed lesson")
    finally:
        coach_service._client = original

    assert isinstance(seen["system"], str)


def test_quiz_still_works_end_to_end_through_the_fake():
    result = coach_service.generate_quiz(
        _learner("Adeola", "l1", "CSS Flexbox"), "CSS Flexbox", 2
    )
    assert result.topic == "CSS Flexbox"
    assert len(result.questions) == 2
    for q in result.questions:
        assert len(q.options) == 4
        assert q.correct_answer in q.options
