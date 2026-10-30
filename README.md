# ProspectLens

Generates a sourced Prospect Brief from a LinkedIn URL, name+company,
pasted profile text, or LinkedIn PDF export.

## Structure

- `backend/` — FastAPI + Supabase + ARQ worker.
- `frontend/` — Next.js 15 (not yet started, see docs/PHASE_TRACKER.md).

## Local run (backend)

```bash
cd backend
cp .env.example .env   # fill in Supabase/Anthropic/Tavily keys
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload
```

Or via Docker: `docker compose up`.

## Status

See `docs/PHASE_TRACKER.md` and `docs/IMPLEMENTATION_LOG.md` for the
real, current state — only Phase 0 backend scaffolding exists so far.
