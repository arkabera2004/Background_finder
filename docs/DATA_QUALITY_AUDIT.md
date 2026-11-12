# Data Quality Audit — All 3 Existing Chanakya Runs (2026-11-13)

No records deleted, no agent rerun, no new run created for this audit.
All numbers below are read directly from the database.

## Run 1 — `24882912-3ff9-4b78-8d59-be945e636b41` (period `2026-11`)

Offering: 1 offering, version 1 ("GenAI Accelerator" / fintech test ICP — an early test run, not real Wayam products).

| Agent | Status | Retries | Output |
|---|---|---|---|
| Catalogue | completed | 0 | 1 offering |
| Company Scout | completed | 1 | 48 found, 48 selected |
| People Finder | completed | 2 | 48/48 companies, 47 people, 0 failed |
| LinkedIn Resolver | completed | 0 | 49 processed, 0 confirmed, **49 ambiguous**, 0 unresolved |
| Email Hunter | pending | — | blocked: no confirmed identity yet |
| Profile Researcher | pending | — | blocked: same |
| QA & Sync | pending | — | never reached |

Companies/people: 48/48 real, every row has a real `source_url`; 49/49
people have a real `linkedin_url`. Duplicates: **0** (checked domain
and name+company_id grouping). Errors: none persisted (the retries
visible were from the pre-fix era this session already documented in
`FINAL_ACCEPTANCE_REPORT.md`).

## Run 2 — `021ac411-c3cc-40b8-8192-16ba05372c8c` (period `2026-12`)

Offering: 2 offering-snapshot versions (1 offering each — this was the
discovery-quality re-verification run from an earlier session).

| Agent | Status | Retries | Output |
|---|---|---|---|
| Catalogue | completed | 0 | 1 offering (latest version) |
| Company Scout | completed | 0 | 5 found, 5 selected |
| People Finder | completed | 0 | 5/5 companies, 10 people, 0 failed |
| LinkedIn Resolver | completed | 0 | 10 processed, 0 confirmed, **10 ambiguous**, 0 unresolved |
| Email Hunter | pending | — | blocked: no confirmed identity yet |
| Profile Researcher | pending | — | blocked: same |
| QA & Sync | pending | — | never reached |

Smallest, cleanest run: no retries anywhere, no errors, every stage
that ran completed cleanly. Duplicates: **0**.

## Run 3 — `df96c66d-6664-4e7a-9361-6518366727ea` (period `2027-01`)

Offering: 27 real Wayam AI accelerator products (Anvaya through
Chanakya), version 1 — the real-product run from this session's
Chanakya UI transformation work.

| Agent | Status | Retries | Output |
|---|---|---|---|
| Catalogue | completed | 0 | 27 offerings |
| Company Scout | completed | 0 | 157 found, 100 selected |
| People Finder | completed | 0 | 100/100 companies processed, 41 people, **76 companies failed** |
| LinkedIn Resolver | **failed** | 3 | 0 processed — never completed |
| Email Hunter | pending | — | blocked |
| Profile Researcher | pending | — | blocked |
| QA & Sync | pending | — | never reached |

**Errors persisted on this run** (from `people_finder`'s
`output_summary.failures`, 10 shown of 76): a mix of `ReadTimeout`,
`ConnectTimeout`, and — critically — several
`HTTPStatusError: ... '432 ' for url 'https://api.tavily.com/search'`.
This is the same Tavily-quota-exhaustion incident already documented in
`FINAL_ACCEPTANCE_REPORT.md` and `SECURITY_AND_PROVIDER_AUDIT.md`: this
run was live when `SEARCH_PROVIDER` was still `tavily`. The 41 people
that *did* get persisted are real (real `linkedin_url` values). The 59
people this run is missing (100 companies × up to 4 leaders, 41 found)
were simply never found — not fabricated, not duplicated, genuinely
absent. `linkedin_resolver` then failed outright on its first person
(`"Craig Compton" "Connected Vehicles"` — a DuckDuckGo timeout, logged
in `chanakya_agent_executions.error`), and per the project's own
"do not repeatedly orchestrate a failed run" instruction from this
session, has not been retried since the provider switch to DuckDuckGo.
Duplicates: **0**.

## Cross-run findings

- **Duplicate records: zero** in all three runs, both at the company
  (domain) and person (name+company) level — the unique DB constraints
  are holding.
- **Evidence**: every one of the 211 companies and 100 people across
  all three runs carries a real `source_url`/`linkedin_url`. 260
  `chanakya_evidence` rows exist total, consistent with that scale —
  no company or person lacks provenance.
- **Identity resolution**: of 100 people that reached LinkedIn
  Resolver (49 + 10 + 41 pending-not-reached), **zero have been
  auto-confirmed**. This is not a defect — it is the resolver correctly
  refusing to guess among real, noisy search results (documented
  extensively in `docs/FINAL_ACCEPTANCE_REPORT.md`'s 2026-11-10
  discovery-quality section). It does mean none of the three runs has
  reached Email Hunter, Profile Researcher, or QA & Sync yet, purely
  because no human has resolved an ambiguous identity through the
  review queue.

## Best candidate for a controlled acceptance test

**Run 2** (`021ac411-c3cc-40b8-8192-16ba05372c8c`). Reasoning:
smallest (5 companies, 10 people — minimal further live-provider
usage), zero retries/errors on any completed stage, and LinkedIn
Resolver already ran cleanly to completion (unlike Run 3, which is
stuck and would need a retry first). The only thing standing between
this run and Email Hunter/Profile Researcher/QA & Sync is one human
resolving at least one of its 10 ambiguous identities.

**This is a human decision, not an engineering task** — Priority H3/H4
both say not to auto-approve uncertain identities. I have not resolved
any of Run 2's ambiguous people. See `docs/PIPELINE_ACCEPTANCE_TEST.md`
§4 for exactly what's needed to proceed, and the open question for you.
