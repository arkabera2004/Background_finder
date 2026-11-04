# Chanakya Gap Analysis (Phase 0)

Baseline: ProspectLens as of `68623d9` (283 backend tests passing, single-prospect
pipeline, no batch/orchestration layer). This document maps that baseline against
the Chanakya seven-agent monthly GTM engine requested for this repo.

## Scope decision

Chanakya is being built as a new, larger product on top of ProspectLens's
foundations (auth, DB session handling, provider adapter pattern, AI provider
abstraction, export/citation validation), not a rewrite. ProspectLens's
single-prospect pipeline (`ResolveIdentityStage` → `FetchProfileStage` →
`AnalyseCareerStage`) maps to Chanakya's **Agent 04 (LinkedIn Resolver)** +
**Agent 06 (Profile Researcher)** for a single person — it does not cover
company discovery, batch/run-of-runs orchestration, email hunting, or
QA/approval/send.

## What exists and is reusable

| Capability | Existing asset | Reusable for Chanakya as |
|---|---|---|
| Auth / tenancy | `get_current_user`, `AuthenticatedUser`, Supabase JWT | Agent/API auth layer, unchanged |
| Config | `Settings` (pydantic-settings) | Extend with Chanakya provider/limit config |
| DB | SQLAlchemy `Base`, `make_engine`, `get_session`, migrations/0001 | Base for new tables (runs, companies, people, etc.) |
| Persistence patterns | `CompanyRepository`, `ProspectRepository`, owner-scoped CRUD | Pattern to copy for `CompanyRunRepository`, `PersonRepository`, etc. |
| Provider abstraction | `build_ai_provider`, `build_search_provider`, `build_company_crawler`, `build_provider_chain`, `ProviderUnavailableError` | Direct reuse for Agent 02/04/05/06 provider waterfalls |
| Pipeline/stage pattern | `Pipeline`, `StageContext`, `StageResult`, `StageFailedError` | Template for the 7-agent stage runner, extended for Service-Bus-style queued execution |
| Identity disambiguation | `find_identity_candidates`, manual-review pause (`needs_identity_selection`) | Direct precedent for Agent 04's manual review queue |
| Citation/brief validation | `validate_brief`, citation validator dropping fabricated `source_id` | Reuse wholesale for Agent 06/07 brief citations |
| Export | ReportLab JSON/MD/PDF export | Extend for monthly Excel/CSV export (Agent 07) |
| Eval framework | `app/evals/` (`Fixture`, `run_evaluation`) | Reuse for per-agent fixture evals |
| Frontend shell | Sidebar/topbar, dashboard, companies/prospects pages, shadcn/ui | Base shell for new Chanakya dashboard pages |

## What is missing (net-new work, by agent)

1. **Run/offering layer** (new, no prior art): monthly `Run` with config/version,
   offering catalogue + ICP editor, nothing exists today — current `Run`/`RunStore`
   is a single-prospect research run, not a monthly batch run.
2. **Agent 02 Company Scout**: no company-discovery-at-scale, no fit scoring,
   no top-N selection. `CompanyRepository` only stores companies already tied to
   a researched prospect.
3. **Agent 03 People Finder**: no role-mapping or per-company leader-list logic.
4. **Agent 04 LinkedIn Resolver provider waterfall**: current resolver is single
   name+company → search, no Clay-style provider priority chain, no batch queue.
5. **Agent 05 Email Hunter**: does not exist at all — no email discovery or
   verification provider integration.
6. **Agent 07 QA/Sync**: no confidence/completeness scoring across merged
   records, no human-review routing, no email draft + approval-gated send,
   no outcome tracking.
7. **Orchestration**: no job queue (Service Bus/ARQ-equivalent for batch),
   no idempotent/resumable monthly run, no per-stage retry/dead-letter beyond
   the single-prospect pipeline's in-process retry.
8. **Azure deployment**: zero Azure artifacts (no Bicep/Terraform, no Container
   Apps config, no Key Vault wiring) — `docs/DEPLOYMENT.md` only covers a
   free-tier single-service deployment (Railway/Fly/Vercel/Supabase).
9. **Frontend**: no catalogue/ICP editor, no Company Scout/People Finder/
   resolver/email/QA review queues, no run-progress-by-stage view, no
   provider-health/cost dashboard, no export center beyond per-prospect export.

## Sequencing

Given the size of this gap, work proceeds phase-by-phase per the master
prompt (Phase 1 domain foundation → Phase 2 Catalogue Agent → ... → Phase 14),
reusing the table above at each phase rather than rebuilding primitives that
already exist. Each phase gets its own commit(s), test run, and
`docs/PHASE_TRACKER.md` update, consistent with this repo's existing
granular-commit convention.
