# CLAUDE.md

## Product

ProspectLens: turn a LinkedIn URL, name+company, pasted profile text, or
LinkedIn PDF export into a sourced Prospect Brief (career, company, content,
communication style, hooks, priorities/pains, sources). No email generation,
no CRM integration, no bulk research, no Chrome extension (v1 exclusions).

## Stack

- Backend: Python 3.12, FastAPI, Pydantic v2, Supabase (Postgres/Auth/Storage),
  Redis + ARQ, Claude API, Tavily/Exa, Firecrawl/Playwright.
- Frontend: Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui, TanStack Query.
- Monorepo: `backend/` and `frontend/` in this single repo (no separate
  prospectlens-backend/prospectlens-frontend repos exist on GitHub — see
  docs/DECISION_LOG.md).

## Conventions

- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `build:`, `chore:`).
  One atomic change per commit. Push after every commit.
- Backend checks: ruff, mypy, pytest. Never weaken a check to pass it.
- Secrets live only in `.env` (gitignored); `.env.example` documents keys.

## Current status

See docs/PHASE_TRACKER.md for the authoritative phase table and
docs/IMPLEMENTATION_LOG.md for the task-by-task log. Do not trust this
file's prose over those two for "what's actually done."
