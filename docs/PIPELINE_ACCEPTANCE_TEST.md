# Pipeline Acceptance Test Plan — 7 Chanakya Agents (2026-11-13)

Fresh full-suite result at time of writing: **416 passed, 6 skipped**
(the 6 skips are Postgres-specific tests gated behind `TEST_POSTGRES_URL`,
not failures — this backend runs on SQLite by default).

For each agent: what's covered by existing automated tests, and what a
live controlled run (H4) would additionally exercise.

## 1. Catalogue
- Tests: `test_catalogue_api.py`, `test_chanakya_end_to_end.py`
- Covered: input validation (empty/duplicate offerings), persistence,
  versioning on resubmit, tenant isolation.
- Not covered by unit tests, needs live run: real 27-offering scale
  (already exercised live in Run 3).

## 2. Company Scout
- Tests: `test_company_scout.py`, `test_company_scout_api.py`,
  `test_company_discovery.py`, `test_chanakya_tenant_isolation.py`
- Covered: candidate filtering (`is_operating_company_page`, aggregator/
  listicle/VC rejection), per-query failure isolation, output schema,
  idempotency (rerun doesn't duplicate), tenant isolation.
- Not covered: real search-provider latency/rate-limit behavior (only
  mocked providers in unit tests) — live-verified in Runs 1–3.

## 3. People Finder
- Tests: `test_people_finder.py`, `test_people_finder_api.py`,
  `test_chanakya_tenant_isolation.py`
- Covered: LinkedIn-URL validation (`is_linkedin_profile_url`),
  organisation-name rejection, per-company failure isolation, output
  schema, tenant isolation.
- Not covered: the 76-company Tavily-timeout failure mode seen in Run 3
  is a real, live-observed case, not a fixture — no regression test
  reproduces "most queries fail, agent still persists partial results."
  Gap, not a blocker (duplicate-prevention and failure isolation are
  both independently tested).

## 4. LinkedIn Resolver
- Tests: `test_linkedin_resolver.py`, `test_linkedin_resolver_api.py`
- Covered: evidence-based rejection (`page_mentions_company`), per-person
  failure isolation (`test_linkedin_resolver_survives_one_persons_search_failure`),
  ambiguous-vs-confirmed output schema, never auto-confirms without
  evidence.
- Not covered: retry-and-recover after a fully-failed run (Run 3's
  state) — no automated test exercises "resume a `failed` agent
  execution," only "survive one person's failure within an otherwise-
  OK run."

## 5. Email Hunter
- Tests: `test_email_hunter.py`, `test_email_hunter_api.py`
- Covered: pattern generation (`generate_candidate_emails`), risky-email
  flagging, requires confirmed identity before running (blocked state
  verified).
- Not covered: no run in this database has reached this agent yet
  (all 3 runs stop at LinkedIn Resolver) — zero live evidence either way.

## 6. Profile Researcher
- Tests: `test_profile_researcher.py`, `test_profile_researcher_api.py`
- Covered: brief validation (`validate_brief`), AI-provider error
  handling, requires confirmed identity.
- Not covered: same as above — no run has reached this agent live.

## 7. QA & Sync
- Tests: `test_qa_sync.py`, `test_qa_sync_api.py`,
  `test_chanakya_tenant_isolation.py`
- Covered: confidence scoring (`score_confidence`), approve/reject flow,
  export-only-approved-records behavior, tenant isolation (needs-you
  endpoints never leak cross-owner).
- Not covered: same as above — no run has reached this agent live.

## Cross-cutting
- **Duplicate prevention**: tested at the unit level (unique constraints)
  and independently confirmed at the data level across all 3 real runs
  in `docs/DATA_QUALITY_AUDIT.md` (zero duplicates found).
- **Evidence/provenance**: `app/tests/test_evidence.py` plus the same
  live cross-check (260 `chanakya_evidence` rows, 100% coverage).
- **Auth/tenant isolation**: `test_chanakya_tenant_isolation.py` covers
  every cross-run aggregate endpoint added in Phases C/D/F.
- **Idempotency**: covered per-agent (rerunning Company Scout/People
  Finder on an already-populated run does not duplicate rows).

## What H4 (controlled end-to-end test) would add beyond this
Everything above is either unit/integration-tested with fixtures, or
already observed live in Runs 1–3. The one thing never observed live is
**Email Hunter → Profile Researcher → QA & Sync**, because no run has
had a human resolve an ambiguous identity yet. That is the actual gap,
and it requires a human decision (see `docs/DATA_QUALITY_AUDIT.md`
§"Best candidate," Run 2), not more engineering — this plan does not
recommend fabricating a resolution to force the gap closed.
