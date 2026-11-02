# New Chat Handoff — ProspectLens

Written 2026-11-02 because the prior conversation's context filled up. Everything here was
verified against the actual repository and GitHub Actions during this handoff's own audit —
see `docs/PROJECT_CURRENT_STATE.md` for the full evidence trail. Read that file for detail;
this one is the quick-start.

## 1. Project overview and goal

ProspectLens turns a LinkedIn URL, name+company, pasted profile text, or LinkedIn PDF export
into a sourced Prospect Brief (17 sections: identity verification, career timeline, education,
company profiles, activity, personalization hooks, outreach strategy, research gaps, sources,
and more). Free-tier-first: Gemini + DuckDuckGo + trafilatura by default; paid providers
(Anthropic, Tavily, Firecrawl, Bright Data, PDL) are all optional and never auto-selected.

## 2. Repository

Local path: `/Users/arkabera/Desktop/Wayam AI/Background_finder`
GitHub: `https://github.com/arkabera2004/Background_finder.git`
Monorepo: `backend/` (FastAPI) + `frontend/` (Next.js 15).

## 3. Current branch and exact HEAD

`main`, commit `25d5511ded02155d6ffb1c9c322e701cc43cbbea` — local matched `origin/main` at
handoff-writing time. **This repo's checkout appears to be shared with at least one other
concurrently-running session** (HEAD moved once already during this handoff's own audit, from
a commit this session made to one it didn't author) — run `git log -1` and `git fetch && git
log --oneline origin/main -1` yourself before trusting this SHA.

## 4. Verified current condition (summary — full detail in PROJECT_CURRENT_STATE.md)

- Backend: 283 tests pass, ruff clean, mypy (CI invocation) clean.
- Frontend: `tsc --noEmit` clean, eslint 0 errors/3 warnings, `npm run build` succeeds,
  unauthenticated Playwright suite 7/7 pass.
- GitHub Actions `CI` (push-triggered `backend`+`frontend` jobs): **green as of HEAD only** —
  every push from `18b32aa` through the second-to-last commit was **red** on a frontend
  `tsc` issue, fixed by the very last commit. Re-run `gh run list --limit 3` before trusting
  "CI is green" as a standing fact.
- GitHub Actions `e2e-auth` job (manual `workflow_dispatch`, real Supabase+Gemini) had, as of
  the start of this audit, failed on both attempts on record at the step that submits a
  research run and waits for "Completed." **A fix landed mid-audit** (commit `25d5511`,
  `fix(e2e): size timeouts to Gemini's actual worst-case retry latency, not a guess` — not
  authored by this handoff session) raising the completion timeout 260s→420s with a documented
  Gemini-retry root-cause theory. **Not yet confirmed live** — no `e2e-auth` dispatch run exists
  on top of this commit yet. **This is the most important open item right now: trigger that
  run and confirm it actually passes before treating this as resolved.**
- Working tree has two older, lower-stakes uncommitted items (a trivial `.gitignore` addition
  and an untracked, apparently-already-executed plan file) — listed in
  PROJECT_CURRENT_STATE.md §7/§15.

## 5. What has already been completed (do not redo)

Phases 0–7 of `docs/PHASE_TRACKER.md` are implemented and tested (fixture-level, see that
file and PROJECT_CURRENT_STATE.md §4 for exactly what "implemented" means per phase) — auth,
the 7-stage research pipeline, AI synthesis with citation validation, identity
disambiguation, company persistence, brief versioning, rate limiting, retention code, eval
framework, CI gates. **Beyond that, and not yet reflected in PHASE_TRACKER.md until this
handoff's audit updated it**: the Chronos frontend design system, the 17-section deep-research
brief schema rewrite, a unified identity-attribution scorer (subject/namesake/unverified
buckets) with five correctness fixes, an authenticated Playwright E2E suite, and the CI
`next typegen` fix. All of this is real, committed, and pushed — see
`docs/IMPLEMENTATION_LOG.md`'s newest entry and `docs/PHASE_TRACKER.md`'s Phase 8 row for the
exact commit list.

**Do not re-implement**: the identity-attribution scorer, the 17-section brief schema, the
Chronos design tokens, the authenticated E2E suite's setup/navigation/prospect-library specs
(they pass), or the CI typegen fix.

## 6. Exact next task

**First: `git log -1` and `git fetch && git log --oneline origin/main -1`** — this checkout
appeared to be shared with another concurrently-running session during the audit that wrote
this handoff (HEAD moved mid-audit to a commit this session didn't author). Confirm who/what
is active before changing anything.

**Then**: a timeout-increase fix for the `new-research.spec.ts` CI failure was committed
(`25d5511`, 260s→420s on a Gemini-retry-latency theory) but **has not been confirmed to
actually work** — no `e2e-auth` dispatch run exists on top of it yet. Your task: trigger that
run and confirm it passes.

1. `gh workflow run CI` (or find the dispatch option in the Actions tab) — this costs real
   Gemini/Supabase API usage, so don't loop it blindly; one confirming run is the goal.
2. `gh run list --limit 3` then `gh run view <id>` to check the `e2e-auth` job's result.
3. **If it passes**: done — update `PHASE_TRACKER.md`/`KNOWN_LIMITATIONS.md` to say so,
   honestly ("live-verified" only once you've seen it pass, not before).
4. **If it still fails**: the timeout increase was a symptom patch, not the root cause. Pull
   the Playwright trace artifact (`npx playwright show-trace test-results/.../trace.zip`) from
   the failing run and investigate for real — likely suspects worth checking (not
   confirmed): an SSE connection issue specific to CI's network environment; a Gemini
   rate-limit/quota response the pipeline doesn't surface cleanly; the `run_store` in-memory
   limitation (§9/§16 of PROJECT_CURRENT_STATE.md) causing a worker/API mismatch that doesn't
   show up in local dev. Fix with the project's normal TDD discipline (failing test first) —
   this is real product code, not test flakiness to paper over.

## 7. Remaining phases, in order

1. **Fix the e2e-auth pipeline-completion failure** (above — this is the actual next task).
2. Resolve the three dead config surfaces (Exa/Brave search, Jina extraction) — implement or
   remove, don't leave them looking wired-up.
3. Move `Run` storage off in-process memory (Postgres-backed) — unblocks retention.
4. Clean up the two uncommitted working-tree items.
5. Refresh stale prose in `README.md`/`CLAUDE.md`/`docs/SECURITY.md` (not urgent).
6. Actual deployment (Supabase project → Railway/Fly backend → Vercel frontend) — do this
   *after* item 1, not before; deploying a pipeline that doesn't reliably complete is not a
   win.

## 8. Important architecture/implementation decisions already made

- Monorepo, not two repos (`docs/DECISION_LOG.md`).
- Free-tier-first: Gemini/DuckDuckGo/trafilatura are the defaults; every paid provider is
  opt-in via explicit config, never auto-selected (`ai_selector.py`, `search_provider.py`
  both enforce this in code, not just docs).
- Ollama support was **removed** (confirmed in `ai_selector.py`'s own docstring) — if you see
  older references to it (in memory, in an old doc), they're stale; don't resurrect it
  without first finding out why it was removed.
- A completed research Run is never auto-saved as a Prospect — `POST /prospects {run_id}` is
  the only promotion path (tested, Phase 6 decision, still true).
- `docs/brief-schema.json` is generated from the Pydantic model
  (`backend/scripts/generate_brief_schema.py`), never hand-edited — CI fails the build if it
  drifts.

## 9. User requirements and working preferences (from `CLAUDE.md` and observed session
   behavior — follow these)

- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `build:`, `chore:`), one atomic
  change per commit, push after every commit, verify the remote is in sync.
- Backend checks (ruff, mypy, pytest) must stay at 0 errors — never weaken a check to make it
  pass.
- Secrets only in `.env` (gitignored); `.env.example` documents names, never values.
- Work autonomously phase-by-phase without stopping to ask approval for each step, per this
  user's established pattern across sessions — but still stop for anything genuinely
  destructive, credential-requiring, or a real architecture fork (e.g., "should we remove
  Ollama entirely" is exactly the kind of thing worth a one-line flag, not silent action).
- Never fabricate test results, live-verification claims, or deployment status — this
  project's own documentation style (PHASE_TRACKER.md, KNOWN_LIMITATIONS.md) is unusually
  careful about labeling "fixture-tested" vs. "live-verified" vs. "blocked"; match that
  convention exactly in any new doc updates.
- Continue working when a credential/service is unavailable locally — document the blocker,
  use safe local/fixture tests, don't stall waiting for access you don't have (this handoff
  itself did exactly that: it read real CI history via `gh` instead of needing live Supabase
  credentials locally).

## 10. Known blockers and how to proceed around them

- No real Supabase project/credentials available in a fresh local environment — `gh run view`
  on existing CI history is the way to get live-verification evidence without needing local
  credentials (as this handoff did). If you need to actually run the authenticated E2E suite
  yourself, it requires `E2E_EMAIL`/`E2E_PASSWORD` (ask the user for a test account, or use
  `gh workflow run` to trigger it in CI where the secrets already exist).
- No Anthropic/Tavily/Firecrawl/Bright Data/PDL credentials locally — any work touching those
  providers stays fixture-tested until/unless the user supplies keys.
- No deployment accounts (Railway/Fly/Vercel) exist — don't claim deployment status without
  one.

## 11. Verification commands to run before changing anything

```bash
cd "/Users/arkabera/Desktop/Wayam AI/Background_finder"
git status && git log -1 --format="%H %ci %s" && git fetch origin && git log --oneline origin/main -1

cd backend && .venv/bin/python -m pytest -q
.venv/bin/ruff check app main.py
.venv/bin/mypy app main.py --ignore-missing-imports

cd ../frontend && npx tsc --noEmit && npx eslint src && npm run build
npx playwright test --config=playwright.config.ts   # unauthenticated suite, no prereqs

cd .. && gh run list --limit 5   # confirm CI is still green on the latest push
```

## 12. Starter prompt for the new chat

```
You are continuing work on ProspectLens in
/Users/arkabera/Desktop/Wayam AI/Background_finder
(GitHub: https://github.com/arkabera2004/Background_finder.git).

First, read docs/NEW_CHAT_HANDOFF.md, docs/PROJECT_CURRENT_STATE.md,
docs/PHASE_TRACKER.md, and docs/IMPLEMENTATION_LOG.md, in that order.

Then inspect the actual repository and Git state yourself before acting —
run the verification commands in NEW_CHAT_HANDOFF.md §11. Do not trust any
status claim, including in those four docs, without re-confirming it
still holds (things change between sessions).

This checkout appeared to be shared with another concurrently-running
session during the audit that wrote this handoff (HEAD moved mid-audit
to a commit that session didn't author) — confirm current HEAD and
whether anyone else is active before changing anything.

Your task is exactly: trigger the e2e-auth GitHub Actions workflow
dispatch and confirm frontend/e2e/authenticated/new-research.spec.ts now
passes against real Supabase + real Gemini in CI, following the
already-committed timeout fix in commit 25d5511. If it still fails,
diagnose and fix the real root cause (see NEW_CHAT_HANDOFF.md §6 for
starting points) — the timeout increase alone has not been confirmed to
work.

Do not reimplement anything already completed (see §5 of the handoff).
Work autonomously, phase-by-phase, without repeatedly asking for approval
to continue — but do flag anything genuinely destructive, anything
needing a credential you don't have, or a real architecture decision
(e.g., removing/re-adding a provider).

Make small, atomic, conventional commits. Push every commit and verify
the remote is synchronized (git log --oneline origin/main -1). Run the
relevant tests/build after every meaningful change — never weaken a
check to make it pass. Never fabricate test results, API verification,
or deployment status; if something is blocked by a missing credential,
say so plainly, do what you can with local/fixture tests, and move on to
other real work rather than stalling.

Preserve the existing monorepo structure. Keep the Basic Plan free-first
(Gemini/DuckDuckGo/trafilatura default; every paid provider stays
optional and explicitly opt-in). Avoid destructive Git operations, force
pushes, and unrelated scope changes. Update docs/IMPLEMENTATION_LOG.md
and docs/PHASE_TRACKER.md as you go, following their existing
implemented/tested-with-fixtures/live-verified/blocked convention exactly.
```
