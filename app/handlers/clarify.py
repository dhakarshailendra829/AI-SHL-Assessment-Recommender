from app.llm.client import generate_text
from app.llm.prompts import CLARIFY_REPLY_TEMPLATE
from app.schemas import ChatResponse
from app.state import ExtractedSlots


def run(conversation: str, slots: ExtractedSlots) -> ChatResponse:
    suggested = slots.clarifying_question_if_needed or (
        "Could you tell me what role or skill area you're hiring for?"
    )
    prompt = CLARIFY_REPLY_TEMPLATE.format(
        conversation=conversation,
        role=slots.role or "unknown",
        seniority=slots.seniority or "unknown",
        job_level=slots.job_level or "unknown",
        skills=", ".join(slots.required_skills) or "none stated",
        suggested_question=suggested,
    )
    reply = generate_text(
        system_instruction="You write a single, concise clarifying question for a hiring assistant.",
        user_prompt=prompt,
    )
    return ChatResponse(reply=reply or suggested, recommendations=[], end_of_conversation=False)
