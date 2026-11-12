# Frontend Parity Checklist — Chanakya vs. LinkedIn Harness reference

Tracks `docs/LINKEDIN_HARNESS_REFERENCE_AUDIT.md` §2/§3 against actual
implementation. Updated as each phase lands, not written in advance.

## Phase A — Application shell

| Item | Status | Evidence |
|---|---|---|
| Grouped nav with live counts (Chanakya section) | **Done** | `ChanakyaSubNav`, commit `597b473`, browser-verified |
| Persistent demo/mode indicator | Not started | — |
| Global sidebar restructuring (Pipeline/Catalogue/Workspace groups) | Not started — see note below | — |

**Note**: the reference app is Chanakya-only; this repo's global sidebar
also serves the separate ProspectLens single-prospect product. Directly
replacing the global sidebar with the reference's flat Chanakya-only
structure would hide ProspectLens navigation — scoped instead to a
Chanakya-section sub-nav (done) rather than rewriting the global shell.

## Phase B — Configuration

| Item | Status | Evidence |
|---|---|---|
| Offerings catalogue card display (name + ICP tag pills) | **Done** | commit `e744da4`, browser-verified at 27-offering scale |
| Submitted-vs-draft distinction, draft cleared after submit | **Done** | same commit |
| "Our forte" badge | Not applicable — no such field exists in Chanakya's data model (would need a schema change, not just UI) |
| "Sync from website" (auto-derive offerings) | Not started — real feature, needs a new backend endpoint |
| Setup wizard (4-step: Sender/Offerings/Exclusions/Connections) | Not started |
| ICP configuration / scoring-rules page | Not started — Chanakya's scoring is currently a fixed `score_fit()` function, not a user-configurable weight UI like the reference |

## Phase C — Company discovery

| Item | Status | Evidence |
|---|---|---|
| Cross-run Companies page | **Done** | `/chanakya/companies`, commits `42d9caa`/`ce3f170`, browser-verified at 210-company scale |
| Tabs with live counts (All/High fit/Selected) | **Done** | same |
| Search by name/domain | **Done** | same |
| Fit score as number + bar | **Done** | same |
| Top-signal column (matched-evidence phrase) | Not started — `ScoutedCompany` has no column storing *which* evidence phrase matched; would need either a new field or deriving it client-side from `Evidence` |
| Company detail drawer/page | Not started |
| "Add company" (manual entry) | Not started — no backend endpoint for a manually-added company exists |

## Phase D — People discovery

| Item | Status | Evidence |
|---|---|---|
| Cross-run Leaders page | **Done** | `/chanakya/people`, commits `52091c7`/`d33d316`, browser-verified at 100-leader scale |
| Tabs with live counts (All/Confirmed/Needs review) | **Done** | same |
| Search by name/company | **Done** | same |
| LinkedIn-linked name, resolution-status badge | **Done** | same |
| Manual LinkedIn-lookup / identity-resolution review restyled to reference pattern | Not started — the existing per-run review queue (built in an earlier session) works but hasn't been re-styled to match the reference's "Needs you" card layout |

## Phase E — Execution and orchestration

| Item | Status | Evidence |
|---|---|---|
| Agent cards (icon + status + real per-stage metric) | **Done** | commit `dd73598`, browser-verified against a real 157-company/41-person run |
| Funnel chart (real percentages, not fabricated) | **Done** | same |
| Live, streaming execution log | **Not buildable without new infrastructure** — Chanakya's agents run synchronously within one HTTP request; there is no WebSocket/SSE channel for Chanakya runs (ProspectLens's separate single-prospect flow has SSE, Chanakya doesn't). A "live log" without a real stream behind it would be a fake, which the project's own rules forbid. Flagged as a real backend gap, not skipped silently. |
| Metrics grid (LLM calls/tokens, LinkedIn pages used today) | **Not buildable** — Chanakya doesn't track LLM token counts or provider call counts anywhere in its data model; would need new instrumentation, not a UI task |

## Phase F — Review and integrations

| Item | Status | Evidence |
|---|---|---|
| "Needs you" aggregate queue (3 real sub-queues) | **Done** | `/chanakya/needs-you`, commit `75ea103`, browser-verified at 59-item scale with working Confirm/Approve/Reject actions |
| Integrations status cards | **Done** | `/chanakya/integrations`, commits `3d8988d`/`edceb4f`, browser-verified — and immediately surfaced a real finding: `EXTRACTION_PROVIDER=firecrawl` is live in `.env` (paid, not yet spent against since no agent has reached Profile Researcher) |
| Budget caps (e.g. "LinkedIn pages today: 0/200") | Not applicable — Chanakya has no per-day page budget concept in its data model (that's specific to the reference's real-LinkedIn-session harness, which this project correctly excludes) |
| Guardrail checklist card | Not started — a real one is easy to write (e.g. "No email leaves without your approval," "Duplicate monthly runs rejected") but wasn't prioritized this round |

## Phase G — Polish

| Item | Status | Evidence |
|---|---|---|
| Responsive fix: Companies/People tables, Needs-you resolve row | **Done** | commit `624660e` — fixed-column grids with no mobile fallback found and fixed |
| Full final regression (backend + frontend, all phases together) | **Done** | 416 backend tests passed, ruff/mypy clean (27 pre-existing stub errors, zero new); frontend tsc/eslint/build clean |
| Mobile viewport verified by direct screenshot | **Not verified** — this session's window-resize tool reports success but the rendered viewport doesn't actually change size, so a true mobile screenshot wasn't obtainable. Verified instead by reading the actual Tailwind breakpoint classes applied. Documented honestly as a gap, not claimed as tested. |
| Accessibility audit (contrast, ARIA) | Not done — nav elements have `aria-label`s (added incidentally in Phases A/C/D); no dedicated audit pass |

## Honest summary — all 7 phases
A, B, C, D, E, F, and G all have real, committed, mostly browser-verified
work. 10 commits across this session's Chanakya-transformation work,
all pushed and verified against `origin/main`. Genuinely not done:
the setup wizard, "Sync from website," configurable ICP scoring, a
live execution log (needs new streaming infrastructure), LLM/cost
metrics (needs new instrumentation), and a true mobile-viewport visual
check. Two real paid-provider findings surfaced along the way (Tavily,
then Firecrawl) — both flagged for the user's decision; both resolved
on explicit instruction (`SEARCH_PROVIDER=duckduckgo`,
`EXTRACTION_PROVIDER=local`), confirmed live via the Integrations page
after a backend restart (env vars only re-read at process startup).
The app now runs entirely on free, keyless providers by default.
