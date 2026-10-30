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

## Not yet implemented

Rate limiting (30 runs/day, 3 concurrent), audit logging, retention/deletion
jobs, input sanitization for crawled/uploaded content, CORS lockdown beyond
localhost, secret rotation. All Phase 7 scope.

## Compliance

No DPDP Act 2023 or GDPR compliance claim is made. This document records
engineering practice, not a legal assessment.
