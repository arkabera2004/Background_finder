# LinkedIn Harness — Reference Audit (2026-11-11)

Reference codebase inspected: `/Users/arkabera/Desktop/Mriganko Da/linkedinharness`
(not `LinkedIn Harness` — that exact-cased folder does not exist on this machine;
confirmed with the user this is the correct path). Read-only inspection only —
nothing in that directory was modified.

## 0. What this actually is (important correction)

This is **not** a separate, unrelated product with its own design language to
borrow stylistically. It is an **earlier/parallel build of the same product**
— "Chanakya: GTM prospecting engine (local version)", built from the same
"Wayam GTM Prospecting Engine Flow" paper, implementing the same 7 agents
(Catalogue, Company Scout, People Finder, LinkedIn Resolver, Email Hunter,
Profile Researcher, QA and Sync) — plus one extra component:

**`linkedin_harness.py`** — a standalone CLI/library that drives a real,
authenticated LinkedIn session through `browser-use` (an LLM-controlled
browser agent) to search, read profiles/companies/jobs, and (if explicitly
allowed) take write actions (connect, message, like, comment, apply). It
persists a browser profile at `.linkedin-profile/` and a local SQLite cache
at `outputs/linkedin.db`.

**This second component was not run against real LinkedIn in this audit**,
and will not be integrated into Chanakya. See §8 (Compliance) — this is a
direct conflict with both LinkedIn's own Terms of Service and the explicit
compliance rules in the transformation request itself ("do not implement
unauthorised LinkedIn scraping... session-cookie extraction... login
automation that violates LinkedIn restrictions"). Running
`uv run linkedin_harness.py login` would mean automating a real LinkedIn
account session to scrape pages it doesn't officially expose for that — the
exact category of action excluded. The **web UI and the surrounding
7-agent pipeline architecture** were run and inspected live in demo mode
(`CHANAKYA_SOURCES=demo CHANAKYA_LLM=mock`, zero real accounts, zero
network calls to LinkedIn or any paid API) and are the genuinely reusable
part of this reference.

## 1. Architecture

| Layer | This reference | Current Chanakya (Background_finder) |
|---|---|---|
| Backend language | Python, FastAPI (`chanakya/api.py`) | Python, FastAPI |
| Backend persistence | Raw `sqlite3` + hand-written SQL (`chanakya/db.py`) | SQLAlchemy 2.x ORM models |
| Frontend | Next.js 16.4.3, React 19.3.1, Tailwind 4.3.3, `lucide-react` icons | Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui |
| Auth | Local email+password, httpOnly session cookie, 14-day sliding, 5-attempts-then-lockout, owner + members | Supabase Auth (JWT via JWKS) |
| LLM | Provider-chain: Azure OpenAI → Ollama → Anthropic → OpenAI → mock heuristics (`chanakya/llm.py`) | Gemini (default) / Anthropic, configurable |
| Background jobs | In-process async pipeline (`chanakya/pipeline.py`), no queue | ARQ + Redis (cron for retention + the new Phase 5 scheduler) |
| MCP | Serves itself as an MCP server (`chanakya mcp`) and calls Clay/Outlook as MCP clients | None |
| API contract | Hand-documented in `contracts/api.md` | Implicit (FastAPI OpenAPI + typed TS client) |

Both are single-tenant-per-browser-session Next.js-on-FastAPI apps of
comparable size. No fundamental framework incompatibility — Next.js 16 vs 15
and React 19 vs React-in-Next-15 are the main version deltas worth tracking
if any component code is ported literally.

## 2. Complete feature inventory (by sidebar section, as run live)

- **Home** — "Welcome, {name}. Four quick steps before the first run." —
  4-tab setup wizard (Sender / Offerings / Exclusions / Connections), each
  with "Skip step" / "Skip setup" / "Save and next". Below: date, a 5-icon
  agent-pipeline preview strip (Catalogue, Company Scout, People Finder,
  Research, Outreach), and a tagline block ("The right companies. The right
  leaders. One approval.").
- **Needs you** — the human-review inbox. Three labeled queues with live
  counts in the header (`0 LinkedIn lookups`, `0 low confidence`,
  `0 risky emails`): **Manual LinkedIn lookups** (paste a profile URL when
  the harness couldn't resolve one), **Risky emails** (pattern-guessed
  address on a live mail domain, not confirmed), **Low-confidence contacts**
  (fix the email/LinkedIn or drop). Each queue has its own icon-illustrated
  empty state when clear.
- **Monthly runs** — the run-detail page. Live state: status badge + elapsed
  time, 7 agent cards across the top (name, icon, count "85 of 85",
  status: Done/Working/Queued, orange progress underline on the active
  one), a **funnel chart** ("from 85 to 85", kept vs. dropped, with a
  reason breakdown), a **this-run metrics** grid (Leaders, Briefs, Drafts,
  LLM calls, LLM tokens, LinkedIn pages used today, Finished, Elapsed), and
  a **live log** panel on the right (timestamped, auto-scrolling, one line
  per agent action — e.g. "Scout: scored 85 of 85", "Scout: finding
  companies for 'financial services azure'"). Top-right: Progress/Agent
  graph tabs, Pause run, Cancel. Bottom: "Tools this run uses" badges
  (LinkedIn, Google, Excel).
- **Companies** — data table: search box, 3 tabs (All companies / High fit
  85+ / Scored, each with a live count), columns # / Company (name + bold
  domain) / Industry / Size / **Fit score** (number + a filled horizontal
  bar, not just a number) / Best offering (colored pill) / Top signal (the
  actual matched-evidence phrase, e.g. "Moving workloads to Azure this
  year") / Leaders (count) / Status pill. Sorted by fit score descending by
  default. Header actions: "Export to Excel", "Add company" (manual entry).
- **Leaders** — people found per company (not inspected in UI this round
  due to the demo run not completing People Finder before the audit
  window; schema confirms full name, role, company, LinkedIn status, email
  status, confidence).
- **Outreach** — the drafted-email queue awaiting approval before export.
- **Offerings catalogue** — filter chips (All / Other / ★ Tech consulting /
  Paused), each offering as an expandable card: icon, name, one-line
  description, a **"Our forte" badge** for the flagged primary practice,
  and two tag rows — industries (teal pills) and buyer titles (purple
  pills). Header action: **"Sync from website"** (re-derive the offering
  catalogue from the company's own site) and "Add offering".
- **ICP and scoring** — two side-by-side cards (Clients and exclusions —
  one name/domain per line, auto-excludes anyone contacted in the last 90
  days; Sender — name/designation/company/email that signs every drafted
  email), then "This month's ICP brief" with a **"Preview ICP"** action
  that runs only the Catalogue Agent (queries/industries/buyer-titles per
  offering) without searching anything live — a genuinely good pattern:
  let the user see what will be searched before spending any API calls.
- **Metrics and cost** — not opened this round; sidebar labels it clearly
  as a distinct page from Offerings/ICP, implying real per-run cost/usage
  reporting (LLM tokens, LinkedIn pages used) beyond what the run-detail
  page's live metrics panel already shows.
- **Integrations and schedule** — one card per provider, each showing live
  connection state, not just "configured: yes/no":
  - **LinkedIn session** — "Browser agent, read only", "Not logged in",
    "Log in" button (not clicked — see §0/§8).
  - **LLM** — "Scoring, briefs and emails", "Not tested", "Test" button.
  - **Clay** — "Optional. Azure version.", "Not configured (local
    fallbacks in use)" — the app is explicit that it degrades gracefully,
    not silently.
  - **Website scraper** — "Team, press and contact pages for emails and
    patterns", labeled "Built in" (always available, no credential).
  - **Email check** — "Valid = published on their site. Risky = pattern
    guess on a live mail domain", labeled "DNS MX + published-address
    match" (i.e. no paid verification provider at all in this reference —
    it's a free heuristic, not NeverBounce-style API).
  - **Outlook** — "Nothing is sent automatically. Open the .eml in Outlook
    and press Send", labeled "Drafts (.eml) only" — exports a real .eml
    file rather than ever calling a Send API directly.
  - **MCP servers** section: clay / outlook / playwright, each with
    "Not configured" state and a one-line setup hint plus a "Test" button.
  - **Monthly schedule** card: "Automatic runs are off" (explicit, visible
    toggle state, not buried in settings).
  - **Budget caps** card: "LinkedIn pages today: 0 / 200" with a progress
    bar — the daily LinkedIn page budget is a first-class, always-visible
    UI element, not a backend-only limit.
  - **Guardrails** card: a literal checklist visible to the user —
    "No email leaves without your approval", "Skip current clients and
    anyone contacted in the last 90 [days]" (cut off in the screenshot,
    continues below the fold).
- **Navigator** — sidebar label suggests direct access to the
  `li_observe`/`li_click`/`li_scroll` browser-navigation tool surface
  described in the README; not opened (would require the LinkedIn session,
  excluded per §0).
- **Audit log** — sidebar-level nav item; `chanakya/db.py` has a plain
  `audit(action, detail, actor)` helper writing to one table — every
  mutating action appears to log here.
- **Top bar**, present on every page: breadcrumb (e.g. "Catalogue /
  Offerings"), a **"Demo data · Mock LLM" badge** persistently reminding
  the user which mode they're in (this is a real, valuable pattern worth
  adopting — our Chanakya has no equivalent "you are looking at fixture
  data" indicator anywhere), a notification bell, and the primary
  "Run now" button (always reachable, not buried in a sub-page).
- **Sidebar**, present on every page: logo + "GTM" tag, global search
  ("Search companies, people..."), then grouped nav: ungrouped
  (Home/Needs you/Monthly runs), **Pipeline** (Companies/Leaders/Outreach,
  each with a live count badge), **Catalogue** (Offerings/ICP and
  scoring, also with counts), **Workspace** (Metrics and cost/
  Integrations/Navigator/Audit log), and a pinned-to-bottom **LinkedIn
  pages: 0/200** budget strip plus the signed-in user's name/role/email.

## 3. Component inventory (visually distinct, reusable patterns)

- Agent-pipeline progress card (icon + label + count + status text +
  animated progress underline on the active card).
- Funnel bar ("N kept" as a filled bar against "N found", with a
  drop-reason breakdown line).
- Live auto-scrolling log panel with per-line timestamps.
- Metric tile grid (label above value, no borders, dense).
- Data table with: search box, count-bearing filter tabs, a fit-score
  column rendered as number + mini progress bar, colored category pills,
  status pills.
- Expandable catalogue card with a primary/forte badge and two tag-color
  rows (industry vs. buyer-title).
- Integration status card: name, one-line purpose, live connection state
  as its own line (not just a toggle), and a context-appropriate action
  button (Log in / Test / nothing if "Built in").
- Budget/guardrail cards as plain-language checklists and progress bars,
  not hidden settings.
- Persistent "Demo data · Mock LLM" environment badge in the top bar.
- Sidebar nav groups with live count badges per section.
- 4-tab setup wizard with per-step "Skip" affordances (skip one step vs.
  skip the whole wizard — two distinct actions, not one).

## 4. Backend functionality

- `chanakya/pipeline.py` (316 lines) — the actual agent orchestration,
  in-process async, no queue; presumably sequential per the agent cards'
  behavior (one "Working" at a time).
- `chanakya/agents.py` (552 lines) — the 7 agents' logic.
- `chanakya/catalogue.py` (226 lines) — offering/ICP management, including
  the "Sync from website" derivation.
- `chanakya/sources.py` (443 lines) — `LinkedIn` class (talks to the
  `linkedin_harness` browser agent when available), `scrape_site()`
  (built-in website scraper, no credential), email pattern
  detection/guessing + MX-based `verify()`, and `demo_companies` /
  `demo_leaders` / `demo_research` (deterministic, seeded-random demo-mode
  generators — confirms the demo data is fabricated-and-labeled, not
  presented as real).
- `chanakya/adapters.py` (142 lines) — `ClayAdapter`, `OutlookAdapter`:
  thin wrappers that normalize whatever shape a configured Clay/Outlook
  MCP server returns.
- `chanakya/llm.py` (69 lines) — single `ask()` entry point, provider-chain
  selection, `MOCK` mode whenever no LLM key is present at all (never
  silently fails, degrades to heuristics).
- `chanakya/auth.py` (408 lines) — full local auth: owner/member accounts,
  session cookies, lockout after 5 failed attempts/15 min,
  `chanakya reset-password` CLI escape hatch.
- `chanakya/api.py` (798 lines) — the full REST surface for the Next.js
  frontend, contract documented in `contracts/api.md`.
- `chanakya/api_navigator.py` (214 lines) + `chanakya/mcp_server.py`
  (303 lines) + `chanakya/mcp_clients.py` (216 lines) — MCP server/client
  plumbing (Chanakya serving itself over MCP, and calling Clay/Outlook as
  MCP clients).
- `chanakya/web.py` (338 lines) — the older server-rendered app, kept
  working but explicitly superseded by `web/` per the README.

## 5. Database

`chanakya/db.py`: plain `sqlite3`, no ORM, no migration framework visible
in this file — `connect()`, `q()`/`one()`/`exec_()` thin wrappers,
`update(table, id_, **fields)` generic setter, plus small stat/log/notify
helpers (`bump_stat`, `log_line`, `notify`, `audit`). No formal schema file
was located in the time available for this audit; the table names used
(`runs`, settings via `setting()/set_setting()`, companies, leaders,
offerings, audit log) match the UI 1:1 but exact column definitions were
not fully enumerated — **flagged as incomplete**, not guessed.

## 6. API integrations found

| Integration | How it's used | Credential | Status observed |
|---|---|---|---|
| LinkedIn (via `linkedin_harness.py`/`browser-use`) | Company Scout search, People Finder search, LinkedIn Resolver, Profile Researcher | Persisted browser session at `.linkedin-profile/` (a real login, not an API key) | **Excluded from integration — see §0/§8** |
| Azure OpenAI / Ollama / Anthropic / OpenAI (one of, provider-chain) | Scoring, ICP briefs, email drafting | `AZURE_OPENAI_API_KEY` / `OLLAMA_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Not configured in this `.env` (only `OLLAMA_API_KEY=` placeholder, empty) — ran in `mock` heuristic mode |
| Clay (optional) | `find_companies`, `enrich_company`, `find_people`, `find_email` | MCP server config in `mcp.config.json` (not present — `mcp.config.example.json` only) | Not configured; local fallback used |
| Outlook (optional) | Draft creation; sending gated behind a separate explicit confirm | MCP server config | Not configured; exports `.eml` only |
| Website scraper | Team/press/contact pages for emails and name patterns | None (built-in HTTP fetch) | Always available |
| Email verification | DNS MX + published-address match | None | Always available; explicitly **not** a paid verification API (NeverBounce-equivalent) |

## 7. Authentication

Local account system: email + password, bcrypt-class hashing (not
verified byte-for-byte in this audit, but `auth.py` implements the full
flow including a 5-attempts/15-minute lockout and an owner-vs-member
role split). No OAuth, no external IdP, no MFA observed. Session is an
httpOnly cookie, 14-day sliding expiry. A genuinely created local account
(`audit@local.test`, a throwaway created solely for this audit, local
SQLite only, no external service) was used to reach every screen above.

## 8. Compliance finding — LinkedIn access method (read before using §9/§10 below)

`linkedin_harness.py` automates a **real, authenticated LinkedIn browser
session** via `browser-use` to navigate search/profile/company/job pages
and extract data via in-page JavaScript, explicitly detecting and raising
on `LinkedInBlocked` (login wall, checkpoint, CAPTCHA) rather than
bypassing them outright — but the underlying mechanism (automated,
scripted navigation and scraping of a personal LinkedIn account's
authenticated session, including write actions if `allow_write=True`) is
not an officially sanctioned LinkedIn API or Partner Program integration.
It is the kind of browser automation LinkedIn's User Agreement and
Professional Community Policies prohibit for third-party tooling, and it
is explicitly named as out-of-bounds in this transformation's own
instructions ("unauthorised LinkedIn scraping," "session-cookie
extraction," "login automation that violates LinkedIn restrictions").

**Decision: this mechanism is not run, not integrated, and not
reproduced in Chanakya.** Chanakya's existing LinkedIn Resolver
(DuckDuckGo `site:linkedin.com/in` search + manual review queue —
`backend/app/services/identity_resolution.py`) remains the compliant
baseline. If genuine LinkedIn profile/company data access is wanted later,
the compliant paths are: (a) LinkedIn's own official APIs under a
negotiated Partner Program (very restricted access, sales/marketing
partners only, not self-serve), (b) a user-supplied CSV/export the person
downloads from their own LinkedIn account, or (c) continuing the current
search-engine-plus-human-review approach. See
`docs/REQUIRED_APIS_AND_CREDENTIALS.md` §E for detail.

## 9. Dependencies

Python (`pyproject.toml`): `browser-use`, `dnspython`, `fastapi`, `httpx`,
`imageio[ffmpeg]`, `jinja2`, `mcp`, `numpy`, `openpyxl`, `pillow`,
`python-dotenv`, `python-multipart`, `uvicorn`. Package manager: `uv`
(not pip/poetry). Node (`web/package.json`): Next.js 16.4.3, React
19.3.1/React DOM 19.3.1, `clsx`, `lucide-react`, `tailwind-merge`;
dev: Playwright, Tailwind 4, TypeScript 5.9.

## 10. Reuse classification

**Reused directly** (none — no code was copied; see Phase 3/4 plan in
`docs/TRANSFORMATION_ARCHITECTURE.md` for what gets faithfully
reproduced rather than literally copied, given the React 19/Next 16 vs.
React-in-Next-15/shadcn stack difference).

**Adapted** (UI patterns to reproduce in Chanakya's existing Next.js 15 +
shadcn/ui stack, not ported file-for-file): the run-detail page's agent
cards + funnel + live log + metrics grid; the Companies table's fit-score
bar and top-signal column; the Offerings catalogue's tag/forte-badge card
layout and "Sync from website" affordance; the Integrations page's
per-provider live-status card pattern; the "Needs you" triaged-queue
page; the persistent demo/mode badge; the sidebar's grouped nav with
live counts; the budget-cap and guardrail-checklist cards.

**Reimplemented, not reused**: everything backend — Chanakya
(Background_finder) stays on SQLAlchemy + Supabase Auth + ARQ, not raw
SQLite + local-password auth. The UI patterns above get rebuilt against
our existing API contracts, not the reference's `contracts/api.md`.

**Not reusable, with reason**: the LinkedIn browser-automation harness
(§8 — compliance); the raw-SQLite persistence layer (would be a backward
step from the existing SQLAlchemy/Postgres-path schema and its tenant
isolation, retention, and migration work already built); the local
email+password auth system (Chanakya already has Supabase Auth with real
users — replacing it would be a regression, not an improvement); the MCP
server/client plumbing (no current requirement for Chanakya to act as an
MCP server, and Clay/Outlook are optional, unconfigured in both apps
today — tracked as a future option in the credentials doc, not built now).
