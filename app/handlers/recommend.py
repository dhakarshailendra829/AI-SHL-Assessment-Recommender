from app.llm.client import generate_json
from app.llm.prompts import RECOMMEND_REPLY_TEMPLATE
from app.retrieval.embed_store import CatalogStore
from app.retrieval.ranker import MAX_RECOMMENDATIONS, retrieve_candidates
from app.schemas import ChatResponse, Recommendation
from app.state import ExtractedSlots


def _format_candidates(candidates: list[dict]) -> str:
    lines = []
    for c in candidates:
        types = ", ".join(c.get("test_type", []))
        levels = ", ".join(c.get("job_levels", [])) or "not specified"
        duration = c.get("duration_raw") or "not specified"
        lines.append(
            f"- {c['name']} | types: {types} | job levels: {levels} | "
            f"duration: {duration} | {c.get('description', '')}"
        )
    return "\n".join(lines)


def _to_recommendation(entry: dict) -> Recommendation:
    return Recommendation(
        name=entry["name"],
        url=entry["url"],
        test_type=",".join(entry.get("test_type", [])),
    )


def run(conversation: str, slots: ExtractedSlots, store: CatalogStore) -> ChatResponse:
    candidates = retrieve_candidates(store, slots)
    if not candidates:
        return ChatResponse(
            reply="I couldn't find a matching assessment in the SHL catalog for that. "
            "Could you describe the role or skills differently?",
            recommendations=[],
            end_of_conversation=False,
        )

    prompt = RECOMMEND_REPLY_TEMPLATE.format(
        conversation=conversation,
        role=slots.role or "unknown",
        seniority=slots.seniority or "unknown",
        job_level=slots.job_level or "not specified",
        skills=", ".join(slots.required_skills) or "none stated",
        test_type_preference=", ".join(slots.test_type_preference) or "none stated",
        language_preference=slots.language_preference or "not specified",
        max_duration_minutes=slots.max_duration_minutes or "no limit stated",
        candidates=_format_candidates(candidates),
    )

    try:
        result = generate_json(
            system_instruction="You select assessments strictly from the given candidate list "
            "and respond only with the requested JSON.",
            user_prompt=prompt,
        )
        reply_text = result.get("reply", "Here are assessments that match your requirements.")
        selected_names = result.get("selected_names", [])
    except Exception:
        reply_text = "Here are assessments that match your requirements."
        selected_names = [c["name"] for c in candidates[:5]]

    valid_selected = [name for name in selected_names if store.is_valid_name(name)]
    if not valid_selected:
        valid_selected = [c["name"] for c in candidates[:5]]

    valid_selected = valid_selected[:MAX_RECOMMENDATIONS]
    recommendations = []
    seen = set()
    for name in valid_selected:
        entry = store.get_by_name(name)
        if entry and entry["name"] not in seen:
            recommendations.append(_to_recommendation(entry))
            seen.add(entry["name"])

    return ChatResponse(
        reply=reply_text,
        recommendations=recommendations,
        end_of_conversation=False,
    )
