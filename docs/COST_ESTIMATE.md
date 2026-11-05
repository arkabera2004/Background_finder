# Chanakya Cost Estimate

The master prompt's reference architecture diagram gives a rough
estimate of **$170-$300/month**, explicitly called out there as an
estimate from the diagram, not a guaranteed price, and excluding some
services and provider usage. This document breaks that down by service
and names what's actually optional in this codebase today versus what
the diagram assumes.

**Nothing below has been provisioned or billed.** These are published
Azure list-price ranges as of this writing, for the smallest tier that
would run this workload, not a quote.

## Azure infrastructure (the $170-$300 range)

| Service | Smallest viable tier | Rough monthly cost | Required or optional here |
|---|---|---|---|
| Container Apps (API + worker + frontend) | Consumption plan, scale-to-zero | $20-$60 depending on traffic | Required once deployed |
| Container Apps Job (monthly trigger) | Consumption, runs ~once/month | <$5 | Required for the automated monthly run (not yet built as a Job — currently a plain endpoint) |
| Postgres Flexible Server | Burstable B1ms | $15-$30 | Required — SQLite is dev-only |
| Azure Cache for Redis | Basic C0 | $15-$20 | Required for ARQ workers (already used locally) |
| Key Vault | Standard, per-operation | <$5 | Required for secret management |
| Container Registry | Basic | $5 | Required to push images |
| Front Door / WAF | Standard | $35-$50 | Optional — a Container App's own ingress + TLS covers a single-region deployment without it |
| Monitor / App Insights / Log Analytics | Pay-as-you-go, low volume | $10-$30 | Recommended, not strictly required to run |
| Blob Storage (exports/evidence) | Hot tier, low volume | <$5 | Required once exports move off local disk |
| VNet / private endpoints | Per-endpoint | $10-$20 each | Optional — public ingress with Key Vault secrets is a reasonable smaller-scale starting point |

Summed smallest-viable set (no Front Door, no VNet): roughly **$75-$150/month**.
Adding Front Door + VNet private endpoints brings it toward the diagram's
**$170-$300** range.

## External provider usage (NOT included in the Azure estimate above)

Everything in this column is **currently running on a free/null
fallback** in this codebase — none of it has an API key configured, so
none of it has incurred any real cost in this session:

| Provider | Role | Free tier today | Paid cost if enabled |
|---|---|---|---|
| Tavily/Exa (search) | Company/people discovery | `duckduckgo` default, free, keyless | Tavily ~$0.001-$0.005/search past free tier |
| NeverBounce (email verification) | Agent 05 | `NullEmailVerificationProvider` — always "unknown" | ~$0.003-$0.008/verification |
| Clay (company/people/email data) | Not implemented | N/A | Clay's own per-seat/credit pricing |
| Gemini/Anthropic (AI synthesis) | Agent 06/07 | Gemini free tier if a key is set; no key configured here | Usage-based per-token |
| Firecrawl (extraction) | Optional alternative to local trafilatura | Local extraction is free default | Firecrawl's own per-page pricing |

## Cost controls already implemented

- `MAX_CHANAKYA_RUNS_PER_USER_PER_DAY` (default 5) and
  `MAX_RUNS_PER_USER_PER_DAY` (default 30) cap how often expensive
  pipelines can be triggered per owner (Phase 11).
- Every paid provider defaults to a free/null fallback (`NullSearchProvider`,
  `NullEmailVerificationProvider`) — a missing API key never silently
  escalates to a paid call.
- `target_company_count`/`people_per_company` run config caps scale per
  run rather than hard-coding the master prompt's "100 companies / 300-500
  leaders" targets, so a smaller/cheaper test run is always possible.
- Browser workers (not yet built) are explicitly scoped in the master
  prompt as scheduled-job-only, not continuously running, to avoid
  always-on compute cost — carried forward as a requirement for when
  that tier is built.

## What's not yet quantifiable

Browser-based LinkedIn Resolver compute cost, Clay's pricing, and any
Azure OpenAI usage cost are all zero today because none of those
integrations exist yet (see `docs/DEPLOYMENT_AZURE.md` §5). Add them to
this table when built, not before.
