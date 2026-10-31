# Security

## Current posture (honest, not aspirational)

- Auth: Supabase JWT (HS256, `aud=authenticated`) verified in
  `backend/app/core/auth.py`. Unit-tested against forged/invalid signatures
  and missing headers — never tested against a real Supabase-issued token.
- Tenant isolation: every user-owned table in `0001_init.sql` has RLS
  policies scoped to `owner_id = auth.uid()`. **Never applied to a live
  database** — unverified.
- Secrets: `.env` is gitignored in both `backend/` and `frontend/`; only
  `.env.example` templates are committed. No secret has been committed.
- LinkedIn: no scraping, no LinkedIn login, no automation of a personal
  LinkedIn session anywhere in this codebase. `ManualProvider` only accepts
  user-pasted text. `BrightDataProvider`/`PDLProvider` are unimplemented
  stubs.
- Sensitive attributes: nothing in this codebase infers health, religion,
  caste, politics, sexuality, or family circumstances — there is no
  inference logic written yet at all (Phase 4/5 not started).

## Rate limiting

`POST /research` and `POST /research/pdf` enforce a 30-runs/24h cap per
`owner_id` (`app/services/rate_limit.py`), checked against the existing
run store (no separate counter) and returning HTTP 429 over the limit.
Tested with 4 unit tests + 1 HTTP test
(`test_create_research_rate_limited_after_daily_cap`). Not yet implemented:
a concurrent-run cap, and this is in-process memory — it resets on restart
and isn't shared across multiple backend processes.

## Tenant isolation

Every company/prospect/brief/run endpoint filters by `owner_id` at the
repository layer. Cross-owner access returns 404 (not 403, to avoid
confirming the resource exists) — verified by HTTP tests for companies
(`test_get_company_cross_owner_returns_404`,
`test_delete_company_cross_owner_returns_404`), prospects, and brief
versions (`test_get_brief_version_cross_owner_returns_404`).

## Retention

`app/services/retention.py` deletes research Runs older than 90 days;
wired as a daily ARQ cron job (`run_retention_sweep`, 03:00) in
`app/workers/main.py`. Scope is Runs only — a saved Prospect is a
separate, user-initiated record that retention never touches (see the
file's docstring). 4 unit tests cover the cutoff boundary and multi-owner
batches.

**Known limitation**: `run_store` is in-process memory, so the worker
process and the API process do not actually share state yet — this cron
job is correct code against the interface it will use once Runs move to
Postgres, but it cannot delete anything in the current single-process
deployment where the worker never sees the API's runs. Honest status:
IMPLEMENTED, NOT YET EFFECTIVE until Runs are persisted to a shared store.

## Not yet implemented

Audit logging, input sanitization for crawled/uploaded content, CORS
lockdown beyond localhost, secret rotation. Phase 7 scope.

## Compliance

No DPDP Act 2023 or GDPR compliance claim is made. This document records
engineering practice, not a legal assessment.
