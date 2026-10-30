# Canonical Domain Model

Source of truth for cross-cutting types referenced by both the pipeline and
(eventually) the frontend.

## Person (`backend/app/schemas/profile.py`)

Normalized output of any `ProfileProvider`: `full_name`, `headline`,
`current_company`, `linkedin_url`, `experiences: list[Experience]`,
`posts: list[Post]`, `source` (which provider produced it).

## Experience

`title`, `company`, `start_date`/`end_date` (`"YYYY-MM"` or `None` if
current), `description`.

## Post

`text`, `posted_at`, `is_repost`, `url`.

## Research input (`backend/app/schemas/research.py`)

Three intake shapes, one per Pydantic model:
`ResearchByUrl` (validated LinkedIn `/in/` URL, rejects company URLs),
`ResearchByNameCompany`, `ResearchByPastedText` (min 50 chars). A fourth
(PDF upload) is not yet modeled — pending Phase 1 multipart endpoint work.

## Database tables (`backend/migrations/0001_init.sql`)

`prospects`, `companies`, `research_runs`, `run_steps`, `sources`, `briefs`,
`products` — all owner-scoped via `owner_id` + RLS. This is the canonical
persisted shape; `docs/brief-schema.json` (Phase 5, not yet written) will be
the canonical shape for the `briefs.data` JSONB payload specifically.
