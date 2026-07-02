"""
Replays the 10 provided conversation traces against a running /chat endpoint,
using Gemini to play the simulated user from each trace's persona and facts.

Drop the downloaded trace JSON files into tests/test_traces/ before running.
Expected trace schema (one file per persona):

{
  "persona": "Hiring manager for a backend Java role",
  "facts": {
    "role": "Java developer",
    "seniority": "Mid-level, 4 years",
    "skills": ["Java", "stakeholder management"]
  },
  "expected_assessment_names": ["Java 8 (New)", "OPQ32r"]
}

Usage:
    python eval/replay_harness.py --base-url http://localhost:8000 --max-turns 8
"""

import argparse
import json
from pathlib import Path

import requests
from google import genai
from google.genai import types

TRACES_DIR = Path(__file__).resolve().parent.parent / "tests" / "test_traces"

SIMULATED_USER_SYSTEM = """You are role-playing as a hiring manager with this persona: {persona}
Known facts you can share if asked: {facts}
Answer the assistant's questions truthfully using only these facts.
If asked something outside these facts, say you have no preference.
Once the assistant gives you a shortlist of assessments, thank them and say you're done.
Keep replies short, like a real chat message."""


def load_traces() -> list[dict]:
    traces = []
    for path in sorted(TRACES_DIR.glob("*.json")):
        with open(path) as f:
            traces.append(json.load(f))
    return traces


def simulate_user_reply(client: genai.Client, persona: str, facts: dict, history: list[dict]) -> str:
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Conversation so far:\n{history_text}\n\nYour next message:",
        config=types.GenerateContentConfig(
            system_instruction=SIMULATED_USER_SYSTEM.format(persona=persona, facts=json.dumps(facts)),
            temperature=0.4,
        ),
    )
    return (response.text or "").strip()


def recall_at_k(recommended_names: list[str], expected_names: list[str]) -> float:
    if not expected_names:
        return 1.0
    recommended_set = {n.lower() for n in recommended_names[:10]}
    expected_set = {n.lower() for n in expected_names}
    hits = len(recommended_set & expected_set)
    return hits / len(expected_set)


def run_trace(client: genai.Client, base_url: str, trace: dict, max_turns: int) -> dict:
    history: list[dict] = []
    last_response: dict = {}

    opening = simulate_user_reply(client, trace["persona"], trace["facts"], history)
    history.append({"role": "user", "content": opening})

    for _ in range(max_turns):
        resp = requests.post(f"{base_url}/chat", json={"messages": history}, timeout=30)
        resp.raise_for_status()
        last_response = resp.json()
        history.append({"role": "assistant", "content": last_response["reply"]})

        if last_response.get("recommendations") or last_response.get("end_of_conversation"):
            break

        user_msg = simulate_user_reply(client, trace["persona"], trace["facts"], history)
        history.append({"role": "user", "content": user_msg})

    recommended_names = [r["name"] for r in last_response.get("recommendations", [])]
    recall = recall_at_k(recommended_names, trace.get("expected_assessment_names", []))
    return {
        "persona": trace["persona"],
        "turns_used": len(history),
        "recommendations": recommended_names,
        "recall_at_10": recall,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--max-turns", type=int, default=8)
    args = parser.parse_args()

    client = genai.Client()
    traces = load_traces()
    if not traces:
        print(f"No traces found in {TRACES_DIR}. Download and place them there first.")
        return

    results = [run_trace(client, args.base_url, t, args.max_turns) for t in traces]
    mean_recall = sum(r["recall_at_10"] for r in results) / len(results)

    for r in results:
        print(f"- {r['persona']}: recall@10={r['recall_at_10']:.2f}, turns={r['turns_used']}")
    print(f"\nMean Recall@10 across {len(results)} traces: {mean_recall:.3f}")


if __name__ == "__main__":
    main()
