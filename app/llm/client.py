import json
import os
import time
from google.genai.errors import ServerError
from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.state import ExtractedSlots

load_dotenv()

_client: genai.Client | None = None
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        _client = genai.Client(api_key=api_key)
    return _client


def extract_slots(conversation: str) -> ExtractedSlots:
    from app.llm.prompts import SLOT_EXTRACTION_SYSTEM, SLOT_EXTRACTION_USER_TEMPLATE

    schema_instructions = """
Respond with ONLY a single JSON object (no markdown fences, no extra text) with these exact keys:
{
  "role": string or null,
  "seniority": string or null,
  "job_level": string or null,
  "required_skills": array of strings,
  "test_type_preference": array of strings,
  "language_preference": string or null,
  "max_duration_minutes": integer or null,
  "compare_targets": array of strings,
  "is_off_topic_or_injection": boolean,
  "is_general_hiring_or_legal_advice": boolean,
  "has_enough_context_to_recommend": boolean,
  "user_signaled_done": boolean,
  "clarifying_question_if_needed": string or null
}
"""

    response = call_with_retry(
        lambda: get_client().models.generate_content(
            model=MODEL,
            contents=SLOT_EXTRACTION_USER_TEMPLATE.format(conversation=conversation),
            config=types.GenerateContentConfig(
                system_instruction=SLOT_EXTRACTION_SYSTEM + schema_instructions,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
    )
    raw_text = (response.text or "{}").strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        data = {}
    return ExtractedSlots(**data)


def generate_text(system_instruction: str, user_prompt: str, temperature: float = 0.3) -> str:
    response = call_with_retry(
        lambda: get_client().models.generate_content(
            model=MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
        ),
    )
)
    return (response.text or "").strip()


def generate_json(system_instruction: str, user_prompt: str, temperature: float = 0.2) -> dict:
    response = call_with_retry(
        lambda: get_client().models.generate_content(
            model=MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=temperature,
            ),
        )
    )

    raw = (response.text or "{}").strip()

    raw = (
        raw.replace("```json", "")
           .replace("```", "")
           .strip()
    )

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
    
    
    
def call_with_retry(fn, retries=3, delay=1.5):
    last = None

    for i in range(retries):
        try:
            return fn()
        except ServerError as e:
            last = e

            if getattr(e, "code", None) == 503 or "UNAVAILABLE" in str(e):
                if i < retries - 1:
                    time.sleep(delay * (2 ** i))
                    continue

            raise

    raise last