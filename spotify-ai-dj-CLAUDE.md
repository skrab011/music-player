# CLAUDE.md — Spotify AI DJ (working title: "ai-dj")

## What this project is

A personal AI playlist curator. Claude generates playlists from mood/activity/taste prompts using its own music knowledge, then a local Python script pushes them into Jacob's Spotify account via the Web API. Playback happens in the official Spotify app (iPhone, desktop) — this project never plays audio itself.

**Replaces:** Jacob's Apple Music subscription (being cancelled). Goal is zero/near-zero marginal cost using tools he already pays for (Spotify Premium via Duo, Claude subscription).

## Who Jacob is (read this before writing anything)

- Architect, strong domain expertise elsewhere — **coding novice**. Explain every script in plain language alongside code comments. Do not assume familiarity with syntax, patterns, or terminology.
- Expects clarifying questions BEFORE significant output, plan-before-build discipline, and pushback with reasoning when something is wrong or suboptimal.
- Work one phase at a time. Verify acceptance tests pass before moving on.
- Peer-level, casual-direct tone.

## The one architectural fact that shapes everything

**Spotify's API will not help with discovery.** Recommendations, audio features, related artists, top tracks, browse, and popularity were all removed for Development Mode apps (Nov 2024 + Feb 2026 changes). Spotify's role here is exactly two things:

1. **Catalog lookup** — resolve "Artist – Title" strings to track URIs via `GET /search` (max 10 results/request, paginate with `offset`)
2. **Playlist delivery** — `POST /me/playlists` to create, `POST /playlists/{id}/items` to fill

All curation intelligence comes from Claude. Never attempt to call `/recommendations`, `/audio-features`, `/artists/{id}/related-artists`, `/artists/{id}/top-tracks`, or batch endpoints (`GET /tracks?ids=`) — they return 403/404 for this app and time spent debugging them is wasted.

## How the DJ loop works

1. Jacob asks Claude Code for a playlist ("90 minutes of focus music, instrumental lean, some Nujabes energy")
2. Claude consults the taste profile (`taste-profile.md` in this repo) and generates a tracklist as structured data (artist, title, optional album hint)
3. Claude runs `push_playlist.py` with that tracklist
4. Script resolves each track via search, reports misses back, creates/updates the playlist
5. Claude reviews misses, substitutes alternatives, re-runs
6. Playlist appears in Jacob's Spotify app automatically

## Stack (locked)

- **Python 3**, minimal dependencies: `requests` (or `spotipy` only if it has been updated for the Feb 2026 endpoint renames — verify before adopting)
- **Auth:** Authorization Code with PKCE, token cached to a local gitignored file, auto-refresh
- **Runs on:** Jacob's Dell Precision 5510 (Windows) for v1 — Python to be installed there. No server, no hosting, no scheduler in v1. `push_playlist.py` is written Actions-ready (token from env var, tracklist from file, non-interactive) so GitHub Actions is a config-only hosting upgrade later. See handoff Section 10.
- **Curation:** Claude Code session (subscription cost = $0 marginal). Anthropic API backend is a documented future upgrade, not v1.

## Repo hygiene

- `client_id` is fine in config; there is no client secret with PKCE. **Token cache file must be gitignored.**
- `taste-profile.md` — Claude maintains this. Update it when Jacob gives feedback ("less of X", "loved that one").
- Dead ends and corrections get recorded in the handoff doc, never deleted.

## Reference

Full plan, locked decisions, dead ends, phases, and acceptance tests: `spotify-ai-dj-handoff.md`. Interview answers / operating decisions (naming, visibility, explicit, misses, standing playlists, runtime): handoff Section 10.
