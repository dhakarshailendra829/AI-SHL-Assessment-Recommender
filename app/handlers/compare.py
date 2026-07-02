from app.llm.client import generate_text
from app.llm.prompts import COMPARE_REPLY_TEMPLATE
from app.retrieval.embed_store import CatalogStore
from app.schemas import ChatResponse
from app.state import ExtractedSlots


def _format_entry(entry: dict, legend: dict[str, str]) -> str:
    type_names = [legend.get(t, t) for t in entry.get("test_type", [])]
    job_levels = ", ".join(entry.get("job_levels", [])) or "not specified"
    languages = ", ".join(entry.get("languages", [])[:5]) or "not specified"
    duration = entry.get("duration_raw") or "not specified"
    return (
        f"{entry['name']} (url: {entry['url']})\n"
        f"  Test types: {', '.join(type_names)}\n"
        f"  Job levels: {job_levels}\n"
        f"  Languages: {languages}\n"
        f"  Duration: {duration}\n"
        f"  Description: {entry.get('description', 'not available')}"
    )


def run(conversation: str, slots: ExtractedSlots, store: CatalogStore) -> ChatResponse:
    found = []
    missing = []
    for target in slots.compare_targets:
        entry = store.get_by_name(target)
        if entry:
            found.append(entry)
        else:
            missing.append(target)

    if len(found) < 2:
        names = ", ".join(slots.compare_targets) or "the assessments you mentioned"
        return ChatResponse(
            reply=f"I don't have enough matching entries in the SHL catalog to compare {names}. "
            "Could you confirm the exact assessment names?",
            recommendations=[],
            end_of_conversation=False,
        )

    catalog_data = "\n\n".join(_format_entry(e, store.legend) for e in found)
    prompt = COMPARE_REPLY_TEMPLATE.format(conversation=conversation, catalog_data=catalog_data)
    try:
        reply = generate_text(
            system_instruction="You compare assessments using only the catalog data provided, never outside knowledge.",
            user_prompt=prompt,
        )
    except Exception:
        reply = (
            "I couldn't compare the assessments right now due to a temporary error. "
            "Please try again."
    )

    if missing:
        reply += f" (Note: I couldn't find {', '.join(missing)} in the SHL catalog.)"

    return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False)
