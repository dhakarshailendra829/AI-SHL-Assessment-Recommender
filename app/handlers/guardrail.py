from app.llm.prompts import GUARDRAIL_REPLY_ADVICE, GUARDRAIL_REPLY_OFF_TOPIC
from app.schemas import ChatResponse
from app.state import ExtractedSlots


def run(slots: ExtractedSlots) -> ChatResponse:
    if slots.is_off_topic_or_injection:
        reply = GUARDRAIL_REPLY_OFF_TOPIC
    else:
        reply = GUARDRAIL_REPLY_ADVICE
    return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False)
