# Provider Evaluation

## Status: NOT STARTED (blocked on accounts)

Per the project plan, selecting a paid LinkedIn profile provider requires
running a 20-profile trial before committing to production spend. This has
not happened — no Bright Data or People Data Labs account exists.

## Evaluation criteria (to run once trial accounts exist)

For each of the 20 fixture profiles, measure:

1. **Coverage** — did the provider return the profile at all?
2. **Freshness** — how stale is the cached/returned data vs. the live profile?
3. **Post/repost coverage** — how many of the person's recent original posts
   and reposts are returned, compared to manual inspection?
4. **Price per profile** — actual cost at the evaluated tier.
5. **Error rate** — timeouts, malformed responses, rate limiting.

## Decision rule

Pick the provider with the best coverage-per-rupee that also returns post
history (required for Phase 4 activity analysis), unless freshness is bad
enough to materially harm the brief's accuracy. Record the actual numbers
here once measured — do not estimate or assume them.

## Current fallback

`ManualProvider` (`backend/app/providers/profile_provider.py`) is the only
provider that works today. It requires the user to paste profile text or
upload a PDF — no live scraping, no credentials, no network calls. The
provider chain (`backend/app/providers/selector.py`) always falls back to it.
