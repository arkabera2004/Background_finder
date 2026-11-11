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

## Phase B — Configuration (not started)
Setup wizard · Offerings catalogue (tag/forte-badge cards, "Sync from
website") · ICP configuration · Scoring rules.

## Phase C — Company discovery (not started)
Cross-run Companies table (fit-score bar, top-signal column, tabs/search)
— currently only visible nested inside one run's detail page, not as a
standalone cross-run view like the reference.

## Phase D — People discovery (not started)
Cross-run Leaders table. LinkedIn identity resolution UI already exists
(review queue, built this session) — not yet re-styled to reference
patterns.

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
