from enum import Enum
from pydantic import BaseModel, Field

from app.schemas import ChatMessage

MAX_TURNS = 8


class Intent(str, Enum):
    GUARDRAIL = "guardrail"
    CLARIFY = "clarify"
    COMPARE = "compare"
    RECOMMEND = "recommend"


class ExtractedSlots(BaseModel):
    role: str | None = None
    seniority: str | None = None
    job_level: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    test_type_preference: list[str] = Field(default_factory=list)
    language_preference: str | None = None
    max_duration_minutes: int | None = None
    compare_targets: list[str] = Field(default_factory=list)
    is_off_topic_or_injection: bool = False
    is_general_hiring_or_legal_advice: bool = False
    has_enough_context_to_recommend: bool = False
    user_signaled_done: bool = False
    clarifying_question_if_needed: str | None = None


def turn_count(messages: list[ChatMessage]) -> int:
    return len(messages)


def conversation_text(messages: list[ChatMessage]) -> str:
    lines = [f"{m.role}: {m.content}" for m in messages]
    return "\n".join(lines)


def at_turn_cap(messages: list[ChatMessage]) -> bool:
    return turn_count(messages) >= MAX_TURNS


def route_intent(slots: ExtractedSlots) -> Intent:
    if slots.is_off_topic_or_injection or slots.is_general_hiring_or_legal_advice:
        return Intent.GUARDRAIL
    if slots.compare_targets and len(slots.compare_targets) >= 2:
        return Intent.COMPARE
    if slots.has_enough_context_to_recommend:
        return Intent.RECOMMEND
    return Intent.CLARIFY
