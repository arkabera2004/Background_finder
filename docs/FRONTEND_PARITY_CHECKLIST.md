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

## Phase E — Execution and orchestration (not started)
Agent cards with live progress, funnel chart, live log panel, metrics
grid — currently only a plain status-badge list.

## Phase F — Review and integrations (not started)
"Needs you" aggregate queue (currently per-run only) · Integrations
status cards (per-provider live connection state, budget caps,
guardrail checklist).

## Phase G — Polish (not started)

## Honest summary
One phase (A) is complete and browser-verified. Phases B–G are
unstarted — each is itself a multi-file, multi-day scope if done to the
same verified standard as Phase A. Continuing incrementally, one
small atomic change at a time, per the project's own git-discipline
requirement.
