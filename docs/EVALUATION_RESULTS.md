# Evaluation Results

## IMPORTANT: these are SYNTHETIC fixture results, not real-world accuracy

`backend/app/evals/fixtures.py` contains 20 made-up profiles (invented
names, titles, companies) — none are real people. This framework measures
whether the *pipeline* behaves correctly on a fixed input set, not how
well ProspectLens performs on actual LinkedIn profiles. Real-world
accuracy requires running against real profiles, which requires a
provider account and consent — NOT_STARTED.

## Measured results (offline mode — no live search/crawl)

Run via `PYTHONPATH=. .venv/bin/python -m app.evals.run_eval`, 2026-10-30:

```
Mode: offline (manual-mode baseline, no live providers)
Fixtures evaluated: 20 (SYNTHETIC, not real profiles)
Identity resolution accuracy: 100%
Citation coverage: 100% (20/20 claims sourced or marked inference)
Average personalisation hooks per brief: 0.0
Sensitive-content leaks detected: 0
```

### Why these numbers look the way they do

- **Identity resolution = 100%**: expected, not impressive. In manual
  mode (no search provider), `resolve_identity` trusts the submitted name
  directly rather than disambiguating candidates. This metric will
  become meaningful once real identity search is implemented.
- **Citation coverage = 100%**: the rule-based synthesiser only emits a
  claim when it has a real source or explicitly marks it an inference —
  enforced by `app/services/citation_validator.py`. This is a real
  guarantee, not a coincidence of the fixture data.
- **Average hooks = 0.0**: with no search/crawl provider, there are no
  web sources to build hooks from. This is the honest floor — the
  alternative would be fabricating hooks, which this app never does.
- **Sensitive leaks = 0**: scanned for religion/caste/politics/sexuality/
  health/disability keywords across every claim; none of the current
  stages generate this kind of content at all (Phase 4/5 psychological
  inference was never implemented, by design).

## Live-provider mode (not run)

`run_evaluation(use_live_providers=True)` would run the same 20 fixtures
through real DuckDuckGo search and local trafilatura extraction. Not run
for this report — it's slower, rate-limit-dependent, and the fixtures
are synthetic names with no real web presence, so it would mostly measure
"zero results for fictional names," which is not informative. Meaningful
live evaluation needs real (consented) profiles, which is out of scope
without a profile-provider account per docs/PROVIDER_EVALUATION.md.
