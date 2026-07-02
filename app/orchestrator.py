from app.handlers import clarify, compare, guardrail, recommend
from app.llm.client import extract_slots
from app.retrieval.embed_store import CatalogStore
from app.schemas import ChatMessage, ChatResponse
from app.state import Intent, at_turn_cap, conversation_text, route_intent

FALLBACK_RESPONSE = ChatResponse(
    reply="Something went wrong on my end. Could you rephrase what role or skills you're looking to assess?",
    recommendations=[],
    end_of_conversation=False,
)

TURN_CAP_RESPONSE = ChatResponse(
    reply="We've covered a lot here. Based on everything you've shared, I'd recommend narrowing down from the options already discussed, or starting a fresh conversation for a new role.",
    recommendations=[],
    end_of_conversation=True,
)


def handle_chat(messages: list[ChatMessage], store: CatalogStore) -> ChatResponse:
    if not messages:
        return ChatResponse(
            reply="Tell me about the role or skills you'd like to assess for, and I'll suggest SHL assessments that fit.",
            recommendations=[],
            end_of_conversation=False,
        )

    if at_turn_cap(messages):
        return TURN_CAP_RESPONSE

    convo = conversation_text(messages)

    try:
        slots = extract_slots(convo)

        intent = route_intent(slots)

        if intent is Intent.GUARDRAIL:
            response = guardrail.run(slots)

        elif intent is Intent.COMPARE:
            response = compare.run(convo, slots, store)

        elif intent is Intent.RECOMMEND:
            response = recommend.run(convo, slots, store)

        else:
            response = clarify.run(convo, slots)

        if slots.user_signaled_done:
            response.end_of_conversation = True

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return FALLBACK_RESPONSE