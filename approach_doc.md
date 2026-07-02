# Approach Document — SHL Assessment Recommender

## Design choice: deterministic state machine, not a free agent loop

With an 8-turn cap, a 30-second per-call timeout, and a rigid response schema that
"breaks the evaluator" on deviation, a classic ReAct-style agent loop felt like the
wrong tool — one retried tool call or one malformed JSON emission risks a hard-eval
failure. Instead, a Python router decides the conversational mode (clarify / compare
/ recommend / refuse) using rules, and the LLM is only used for two narrow,
schema-constrained jobs per turn: extracting structured slots from the conversation,
and writing the natural-language reply. This makes the non-deterministic part of the
system small and auditable, which directly addresses the "agent design" rubric: the
system decides when to ask, retrieve, answer, or refuse, and a bad LLM turn degrades
gracefully (falls back to the top retrieved candidates or a generic clarifying
question) instead of crashing the conversation.

Because `POST /chat` is stateless, "refine" isn't a special code path. Slots are
re-extracted from the *entire* message history on every call, so when a user adds a
constraint mid-conversation, the next retrieval naturally reflects it — no diffing
logic to maintain, no risk of it falling out of sync with what was actually said.

## Retrieval setup

Each catalog entry (name + test type + job levels + description) is embedded once at startup with
`sentence-transformers/all-MiniLM-L6-v2` into a FAISS `IndexFlatIP` index. A query string built from
the extracted role, seniority, job level, and skills retrieves the top ~25 candidates, which are then
filtered by any stated test-type preference, job level, language requirement, and duration ceiling —
using the same `job_levels`/`languages`/`duration_minutes` fields SHL's own catalog export provides.
The LLM then selects 1–10 from *only* this filtered candidate list; any selected name not found in the
catalog is dropped before the response is built. This two-stage design (retrieve broad, filter on hard
constraints, then let the model choose narrow) keeps Recall@10 high while making hallucinated URLs
structurally impossible, not just instructed against — and it's also what lets the agent give an honest
"the catalog doesn't have a dedicated test for X" answer instead of silently substituting an unrelated
assessment, which matters for the hallucination and coverage-gap behavior probes.

## Prompt design

Prompts are isolated in `app/llm/prompts.py`, one template per conversational mode,
versioned in one place rather than scattered inline. The slot-extraction prompt is
deliberately conservative — it's told never to invent facts, and to require only a
role or skill area (not seniority) before `has_enough_context_to_recommend` flips
true, so the agent doesn't over-clarify on reasonably complete first messages while
still refusing to act on "I need an assessment" alone. The compare prompt is given
*only* the two catalog records in question and explicitly told not to use prior
knowledge, so a question like "difference between X and Y" is answered from scraped
data, not the model's training memory.

## Evaluation approach

Two layers, mirroring how SHL's own harness works:

1. **Unit/schema tests** (`tests/`) — mock all LLM calls, assert response shape,
   URL provenance, turn-cap enforcement, and guardrail refusals. These run in CI
   without an API key.
2. **Replay harness** (`eval/replay_harness.py`) — a Gemini-driven simulated user
   plays each of the 10 provided personas against a live `/chat` endpoint, ending
   the conversation once a shortlist arrives, and reports Recall@10 per trace.

[Fill in after running: mean Recall@10 = X.XX across N traces; behavior-probe
pass rate = X/X]

## What didn't work / changed during iteration

- Initially considered a full LangGraph agent graph with tool-calling for retrieval.
  Dropped it: the turn/timeout budget rewarded predictability over flexibility, and
  a hand-rolled router is easier to reason about and debug than a graph with
  implicit retries.
- Originally treated "refine" as a state requiring diff-against-previous-slots
  logic. Replaced with full re-extraction every turn once it became clear the
  stateless API meant this was simpler and strictly more robust to out-of-order
  user input.
- Catalog scraping: the product-catalog page turned out to be plain server-rendered
  HTML with simple `?start=N&type=1` pagination (not a JS-rendered table as
  initially assumed), so the scraper is a straightforward `requests` +
  `BeautifulSoup` script rather than a headless-browser one.

## Stack and AI-tool usage

FastAPI + Pydantic for the API/schema layer, FAISS + sentence-transformers for
retrieval, Gemini 2.5 Flash for NLU/NLG, deployed on Render. Claude was used as an
AI pair-programmer for scaffolding the handler/orchestrator structure, the scraper,
and the test suite; all design decisions (state-machine vs. agent loop, retrieval
strategy, hallucination guard) were made and verified by me, and I can walk through
any file in the technical deep-dive.
