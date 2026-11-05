# Azure Deployment Guide (Chanakya)

**Status: documentation and configuration templates only. No Azure
resource of any kind has been provisioned or verified as part of this
work.** This maps the master prompt's 7-layer architecture to what
exists in this repo today, and lists exactly what provisioning a real
environment would require. Treat every command below as a guide to run
yourself, not a record of something already run.

## 1. What exists today vs. what Azure needs

| Master prompt layer | This repo today | Azure target |
|---|---|---|
| Entry (web app) | Next.js app, `frontend/Dockerfile` (standalone build, container **not** build-verified — see `docs/PHASE_TRACKER.md` Phase 13) | Azure Container Apps + Front Door/WAF + Entra ID auth |
| Orchestration | One synchronous `POST /chanakya/runs/{id}/orchestrate` endpoint (Phase 9) — no queue, no scheduled job | Container Apps Job (monthly cron) + Service Bus queues between agents + per-agent worker processes |
| AI models | `GeminiProvider`/`AnthropicProvider`, API keys in `.env` (gitignored) | Azure OpenAI or Claude-on-Foundry, Key Vault + managed identity, no keys in source |
| Browser agent | Not implemented — LinkedIn Resolver's search-only waterfall (Phase 5) has no Playwright/browser tier yet | ACR image + Playwright runtime + browser worker + optional Azure Files volume |
| MCP/external services | `search_provider.py`, `email_verification_provider.py` — DuckDuckGo/null defaults, Tavily/NeverBounce optional, Clay not implemented | Clay MCP, Graph (send, not implemented), configured search, NeverBounce |
| Data | SQLite locally (`DATABASE_URL=sqlite:///...`); ORM already Postgres-compatible, no migration run against real Postgres | Azure Database for PostgreSQL Flexible Server, Azure Cache for Redis (ARQ already expects `redis://`), Blob Storage for exports |
| Security/ops | `.env`/`.env.example`, GitHub Actions CI (`ci.yml`) | Key Vault, VNet/private endpoints, Monitor/App Insights/Log Analytics, cost alerts, ACR + Container Apps CD |

## 2. Provisioning steps (not yet run)

```bash
# Resource group
az group create -n chanakya-rg -l eastus

# Container Registry
az acr create -n chanakyaacr -g chanakya-rg --sku Basic

# Postgres Flexible Server
az postgres flexible-server create -g chanakya-rg -n chanakya-pg \
  --sku-name Standard_B1ms --storage-size 32 --version 16

# Redis (for ARQ)
az redis create -g chanakya-rg -n chanakya-redis --sku Basic --vm-size c0

# Key Vault
az keyvault create -g chanakya-rg -n chanakya-kv

# Container Apps environment
az containerapp env create -g chanakya-rg -n chanakya-env
```

Then build/push each image and create Container Apps:

```bash
az acr build -r chanakyaacr -t chanakya-api:latest backend/
az acr build -r chanakyaacr -t chanakya-frontend:latest frontend/

az containerapp create -g chanakya-rg -n chanakya-api \
  --environment chanakya-env --image chanakyaacr.azurecr.io/chanakya-api:latest \
  --target-port 8000 --ingress external \
  --secrets database-url=keyvaultref:... redis-url=keyvaultref:... \
  --env-vars DATABASE_URL=secretref:database-url REDIS_URL=secretref:redis-url
```

The monthly trigger becomes a Container Apps Job (`az containerapp job
create --trigger-type Schedule --cron-expression "0 3 1 * *"`) once Phase
9's orchestrator is extended into a real queued job — today it is a plain
HTTP endpoint a human or a simple external scheduler (e.g. GitHub Actions
`workflow_dispatch` on a cron, already the pattern this repo uses for
`e2e-auth` in `ci.yml`) would call instead.

## 3. Environment variables per service

API/worker container needs everything in `backend/.env.example`, plus
(once provisioned, via Key Vault references, never committed):

- `DATABASE_URL` → Postgres Flexible Server connection string
- `REDIS_URL` → Azure Cache for Redis connection string
- `SUPABASE_*` → if staying on Supabase auth, or swap for Entra ID (not implemented — current auth is Supabase JWT, see `app/core/auth.py`)
- `AI_PROVIDER`/`GEMINI_API_KEY`/`ANTHROPIC_API_KEY` → or Azure OpenAI equivalents once that provider adapter is built (not implemented — `build_ai_provider` only supports gemini/anthropic today)
- `SEARCH_PROVIDER`, `TAVILY_API_KEY`, etc. — unchanged
- `EMAIL_VERIFICATION_PROVIDER`, `NEVERBOUNCE_API_KEY` — unchanged

Frontend container needs `NEXT_PUBLIC_API_URL` pointed at the API
Container App's ingress URL, plus Supabase public env vars.

## 4. Health checks and rollback

- Backend already exposes `GET /health` (used by `docker-compose.yml`
  implicitly and by CI); wire it as the Container App's liveness probe.
- Container Apps revisions give rollback for free — `az containerapp
  revision list` / `az containerapp ingress traffic set` to shift traffic
  back to a prior revision. No custom rollback tooling exists or is
  needed beyond that.
- No blue/green or canary strategy is configured; default Container Apps
  single-revision-mode behavior applies.

## 5. What this guide does not cover (because it isn't built)

- A real Service Bus-based agent queue (Phase 9 remainder)
- The browser-based LinkedIn Resolver tier and its Playwright worker
- Azure OpenAI as an AI provider option
- Entra ID auth (current auth is Supabase JWT end-to-end)
- Any actual deployment, however small, to a real Azure subscription

See `docs/COST_ESTIMATE.md` for what each of the above would add to the
monthly bill if built.
