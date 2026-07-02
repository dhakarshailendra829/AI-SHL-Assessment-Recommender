from app.retrieval.embed_store import CatalogStore
from app.state import ExtractedSlots

MAX_RECOMMENDATIONS = 10
RETRIEVAL_POOL_SIZE = 25

NORMALIZE = {
    "personality": "P",
    "personality test": "P",
    "personality tests": "P",
    "knowledge": "K",
    "knowledge test": "K",
    "knowledge tests": "K",
    "simulation": "S",
    "simulation test": "S",
    "simulation tests": "S",
}


def build_query(slots: ExtractedSlots) -> str:
    parts = []

    for value in (
        slots.role,
        slots.seniority,
        slots.job_level,
    ):
        if value:
            parts.append(value)

    parts.extend(slots.required_skills)

    return " ".join(parts) if parts else "general assessment"

def retrieve_candidates(store: CatalogStore, slots: ExtractedSlots) -> list[dict]:
    query = build_query(slots)
    candidates = store.search(query, top_k=RETRIEVAL_POOL_SIZE)

    # ------------------------
    # Filter by assessment type
    # ------------------------
    if slots.test_type_preference:
        wanted = set()

        for t in slots.test_type_preference:
            key = t.strip().lower()
            wanted.add(NORMALIZE.get(key, t.upper()))

        filtered = [
            c
            for c in candidates
            if wanted.intersection(set(c.get("test_type", [])))
        ]

        if filtered:
            candidates = filtered

    # ------------------------
    # Filter by job level
    # ------------------------
    if slots.job_level:
        job_level_lower = slots.job_level.lower()

        filtered = [
            c
            for c in candidates
            if (
                not c.get("job_levels")
                or any(
                    job_level_lower in jl.lower()
                    or jl.lower() in job_level_lower
                    for jl in c["job_levels"]
                )
            )
        ]

        if filtered:
            candidates = filtered

    # ------------------------
    # Filter by language
    # ------------------------
    if slots.language_preference:
        lang_lower = slots.language_preference.lower()

        filtered = [
            c
            for c in candidates
            if (
                not c.get("languages")
                or any(
                    lang_lower in lang.lower()
                    for lang in c["languages"]
                )
            )
        ]

        if filtered:
            candidates = filtered

    # ------------------------
    # Filter by duration
    # ------------------------
    if slots.max_duration_minutes:
        filtered = [
            c
            for c in candidates
            if (
                c.get("duration_minutes") is None
                or c["duration_minutes"] <= slots.max_duration_minutes
            )
        ]

        if filtered:
            candidates = filtered

    return candidates[:RETRIEVAL_POOL_SIZE]