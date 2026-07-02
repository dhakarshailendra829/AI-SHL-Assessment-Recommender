# SHL Assessment Recommender

A conversational agent that takes a hiring manager from a vague intent to a grounded
shortlist of SHL Individual Test Solutions, via clarify / recommend / refine / compare
dialogue — built for the SHL Labs AI Intern take-home.

## Architecture

The agent is a deterministic conversation-state machine wrapped around two targeted
Gemini calls per turn, not a free-form agent loop. This keeps every response
schema-valid under an 8-turn cap and a 30-second timeout.

```
POST /chat
   │
   ▼
extract_slots()        — one Gemini call: NLU over full history -> ExtractedSlots
   │
   ▼
route_intent()          — pure Python rules, no LLM, decides the mode:
   │                       GUARDRAIL | CLARIFY | COMPARE | RECOMMEND
   ▼
handler.run()           — one more Gemini call (clarify/compare/recommend only;
   │                       guardrail is template-only, zero LLM calls)
   ▼
ChatResponse             — validated Pydantic schema, only catalog URLs allowed
```

Because the API is stateless, "refine" is not a separate code path — slots are
re-extracted from the full history on every call, so a changed constraint
naturally produces a different shortlist without any diffing logic to maintain.

Retrieval is a FAISS index over `sentence-transformers/all-MiniLM-L6-v2` embeddings
of each catalog entry's name + test type + description, optionally filtered by
stated test-type preference. The LLM is given only the retrieved candidates and is
required to choose from them; any name it returns that isn't in the catalog is
dropped before the response is built — this is what prevents hallucinated URLs from
reaching the schema, even if the model invents one.

## Project layout

```
app/
  main.py              FastAPI app, /health, /chat
  schemas.py           Pydantic request/response models (exact API spec)
  state.py             ExtractedSlots, intent routing, turn-cap logic
  orchestrator.py       ties it together, never lets an exception break the schema
  handlers/             clarify / recommend / compare / guardrail
  retrieval/             embed_store (FAISS), ranker (hybrid filter)
  llm/                   client (Gemini wrapper), prompts (versioned templates)
  catalog/catalog.json   scraped Individual Test Solutions
scripts/scrape_catalog.py   re-run this to refresh the catalog
eval/replay_harness.py      local Recall@10 measurement against the 10 traces
tests/                       schema + guardrail tests, mocked LLM calls
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.tx
cp .env.example .env   # add your GEMINI_API_KEY
```


### Replace with

````md
## Running locally

```bash
pytest tests/ -v
uvicorn app.main:app --reload
curl http://localhost:8000/health
````
## Catalog data

`app/catalog/catalog.json` ships with **106 real catalog entries** sourced directly from SHL's
live scraped catalog export (the same `entity_id`/`job_levels`/`languages`/`duration`/`description`/`keys`
schema you get from the catalog page), covering every assessment referenced in SHL's own example
conversation transcripts — Java/Spring/SQL/AWS/Docker, OPQ32r and its report family, Verify G+ and the
Verify ability suite, DSI and the Manufacturing Safety & Dependability bundle, HIPAA/Medical Terminology,
MS Office simulations, SVAR spoken-language screens, contact-center simulations, Graduate/Executive/
Management Scenarios, GSA, and the Sales Transformation reports — plus broad coverage across engineering,
finance, and general-knowledge domains. All 8 SHL test-type categories are represented.

Retrieval and grounding use the full metadata set, not just name/description:
- **job_levels** — filters candidates against a stated seniority (Entry-Level, Graduate, Mid-Professional,
  Director, etc.)
- **languages** — filters when a language constraint is stated (e.g. "Latin American Spanish")
- **duration_minutes** — filters against a stated time budget
- **test_type** — filters against an explicit test-type preference (K, P, A, S, etc.)

This is a substantial, faithful subset rather than the full 372-item catalog — retyping all 372 records
by hand risked transcription errors at that volume. To get the complete set:

```bash
python scripts/transform_catalog.py raw_catalog_export.json
```

`scripts/transform_catalog.py` converts SHL's raw scraped-export schema (the one with `entity_id`,
`link`, `job_levels`, `languages`, `duration`, `keys`) directly into `app/catalog/catalog.json` — point
it at the full export and it produces the same schema this repo already uses, so no other code changes
are needed. Re-run the FastAPI service afterward so the FAISS index picks up the new entries.

## Testing

```bash
pytest tests/ -v
```

Schema and guardrail tests mock the Gemini calls, so they run without an API key.

## Evaluation

Drop the 10 provided conversation traces into `tests/test_traces/` (see the
docstring in `eval/replay_harness.py` for the expected JSON shape), then:

```bash
uvicorn app.main:app &
python eval/replay_harness.py --base-url http://localhost:8000
```

This mirrors SHL's own evaluator: a Gemini-driven simulated user answers from the
persona's fact sheet, ends the conversation once a shortlist arrives, and the
script reports Recall@10 per trace plus the mean.

## Deployment (Render)

1. Push this repo to GitHub.
2. New Web Service on Render → connect repo → it picks up `render.yaml` and the
   `Dockerfile` automatically.
3. Set `GEMINI_API_KEY` in the Render dashboard environment variables.
4. First `/health` call after a cold start can take up to the platform's wake
   time; the FAISS index is built at startup (in the lifespan handler) so it's
   ready before the first `/chat` call, not lazily on the first request.
