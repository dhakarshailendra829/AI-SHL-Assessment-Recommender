import json
import re
import sys
from pathlib import Path

KEY_TO_CODE = {
    "Ability & Aptitude": "A",
    "Biodata & Situational Judgment": "B",
    "Biodata & Situational Judgement": "B",
    "Competencies": "C",
    "Development & 360": "D",
    "Assessment Exercises": "E",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
}

CODE_TO_NAME = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}


def parse_duration_minutes(duration_str: str) -> int | None:
    if not duration_str:
        return None
    match = re.search(r"(\d+)", duration_str)
    return int(match.group(1)) if match else None


def transform(raw_entries: list[dict]) -> dict:
    assessments = []
    seen_urls = set()
    for entry in raw_entries:
        url = entry.get("link", "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        keys = entry.get("keys", [])
        test_type = sorted({KEY_TO_CODE[k] for k in keys if k in KEY_TO_CODE})
        if not test_type:
            continue

        assessments.append({
            "name": entry.get("name", "").strip(),
            "url": url,
            "test_type": test_type,
            "description": (entry.get("description") or "").strip(),
            "job_levels": entry.get("job_levels", []),
            "languages": entry.get("languages", []),
            "duration_minutes": parse_duration_minutes(entry.get("duration", "")),
            "duration_raw": entry.get("duration", ""),
            "remote": entry.get("remote", "yes"),
            "adaptive": entry.get("adaptive", "no"),
        })

    return {"test_type_legend": CODE_TO_NAME, "assessments": assessments}


def main():
    if len(sys.argv) < 2:
        print("Usage: python transform_catalog.py raw_catalog.json")
        sys.exit(1)
    raw_path = Path(sys.argv[1])
    with open(raw_path) as f:
        raw_entries = json.load(f)

    output = transform(raw_entries)
    out_path = Path(__file__).resolve().parent.parent / "app" / "catalog" / "catalog.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"Transformed {len(output['assessments'])} assessments -> {out_path}")


if __name__ == "__main__":
    main()
