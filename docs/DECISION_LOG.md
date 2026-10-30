# Decision Log

## 2026-10-30: Monorepo instead of two repos

Spec calls for `prospectlens-backend` and `prospectlens-frontend` as
separate GitHub repos. Only one repo exists (`Background_finder`,
empty). User chose a monorepo (`backend/`, `frontend/` subdirectories)
rather than creating two new GitHub repos. Least disruptive given
current state; revisit if the user later wants a split.

## 2026-10-30: Stray home-directory git repo

`~/Desktop/Wayam AI/Background_finder` was an empty directory with no
`.git` of its own; running git there resolved to an accidental repo
rooted at `~` with an unrelated remote (`samadrita-valentine-search`)
and unrelated commit history. Fixed by deleting the empty directory
and `git clone`-ing the real GitHub repo into its place, giving it an
isolated `.git`. The stray `~/.git` repo was left untouched and
flagged to the user as a separate, unresolved risk.

## 2026-10-30: No live external credentials

Supabase, Anthropic, Tavily/Exa, Firecrawl, Railway/Render, Vercel
credentials do not exist yet. Phase 0 code is written to read all of
these from environment variables (see `backend/.env.example`) but
nothing has been provisioned, migrated, or deployed live. Anything
claiming "VERIFIED" against a live service is false until credentials
are supplied.
