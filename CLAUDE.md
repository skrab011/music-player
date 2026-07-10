# CLAUDE.md — AI DJ (personal playlist curator)

## What this project is

A personal AI playlist curator, **built and running**. Claude generates playlists
from mood/activity/taste prompts using its own music knowledge, then
`push_playlist.py` (running in GitHub Actions) resolves the tracks against
Spotify's catalog and creates/updates the playlist on Jacob's account. Playback
happens in the official Spotify app — this project never plays audio itself.

**Current state:** 8 standing "AI DJ —" playlists live on Jacob's account
(Chill · Hype · Heavier · Summer · Workout · Country · Focus, plus the custom
Soft & Moody). The first 7 refresh themselves weekly with discovery picks
(Fridays 18:00 UTC, `rotate-playlists.yml`). On-demand playlists are made by
writing a spec and dispatching the `Build Playlist` workflow.

**Replaces:** Jacob's Apple Music subscription (cancelled). Zero/near-zero
marginal cost on tools he already pays for (Spotify Premium via Duo, Claude
subscription; the weekly rotation costs ~$0.26/run in API usage).

## Who Jacob is (read this before writing anything)

- Architect, strong domain expertise elsewhere — **coding novice**. Explain every script in plain language alongside code comments. Do not assume familiarity with syntax, patterns, or terminology.
- Expects clarifying questions BEFORE significant output, plan-before-build discipline, and pushback with reasoning when something is wrong or suboptimal.
- Peer-level, casual-direct tone.

## The one architectural fact that shapes everything

**Spotify's API will not help with discovery.** Recommendations, audio features, related artists, top tracks, browse, and popularity were all removed for Development Mode apps (Nov 2024 + Feb 2026 changes). Spotify's role here is exactly two things:

1. **Catalog lookup** — resolve "Artist – Title" strings to track URIs via `GET /search` (max 10 results/request, paginate with `offset`)
2. **Playlist delivery** — `POST /me/playlists` to create, `POST`/`PUT /playlists/{id}/items` to fill/replace

All curation intelligence comes from Claude. Never attempt to call `/recommendations`, `/audio-features`, `/artists/{id}/related-artists`, `/artists/{id}/top-tracks`, or batch endpoints (`GET /tracks?ids=`) — they return 403/404 for this app and time spent debugging them is wasted.

## How to run the DJ loop (the ongoing operation)

**On-demand playlist:**
1. Jacob asks for a playlist ("90 minutes of focus music, instrumental lean, some Nujabes energy")
2. Read `taste-profile.md` (including its Do-Not-Play rules) and generate a tracklist
3. Write it to `specs/<name>.json` (format in `push_playlist.py`'s header; `mode: "create"` first time, `"update"` thereafter)
4. Commit + push the spec to `main`
5. Dispatch **`Build Playlist`** (`build-playlist.yml`, ref `main`, input key `spec`) via the GitHub MCP `actions_run_trigger`
6. Read the run logs (`get_job_logs`); **eyeball the matched *titles*, not just the counts** (a "confident" match can still be the wrong version); substitute misses/weak matches in the spec and re-dispatch if needed

**Maintaining a standing playlist:** edit its `specs/<name>.json` (already `mode: "update"` → replaces in place), commit to `main`, dispatch `Build Playlist`.

**Weekly rotation (runs itself):** `rotate-playlists.yml` (Fridays 18:00 UTC, also `workflow_dispatch`) runs `generate_rotations.py` — the Anthropic API generates fresh "adjacent deep cut" picks per lane, guided by `taste-profile.md` and `rotation-history/` (recent weeks' picks, fed back as "don't repeat these") — then builds all 7 via `push_playlist.py` and commits the refreshed specs + history back to `main`. Soft & Moody is NOT in the rotation; it only changes on request.

**Feedback:** when Jacob reacts in plain language ("less ambient", "loved that one"), append a dated entry to `taste-profile.md`'s feedback log — additive, never rewrite history.

## Environment facts (don't rediscover)

- **All Spotify calls happen in GitHub Actions** (or on Jacob's machine). The cloud Code sandbox's egress policy blocks `accounts.spotify.com` — this Claude cannot run `push_playlist.py` or token exchanges directly.
- **Repo secrets:** `SPOTIFY_REFRESH_TOKEN` (delivery) and `ANTHROPIC_API_KEY` (rotation curation; spend-capped workspace key).
- **The Spotify app caches the library** — a new playlist may not show on the phone until the app is force-restarted. `push_playlist.py` prints a direct `open.spotify.com/playlist/<id>` link on every run; check that before assuming anything's broken.

## Repo map

| Path | What it is |
|---|---|
| `push_playlist.py` | The delivery engine: spec JSON → search/match → create-or-update playlist. |
| `generate_rotations.py` | Weekly curation: Anthropic API → fresh specs for the 7 rotating lanes. |
| `spotify_auth.py`, `config.py`, `get_token.py`, `print_refresh_token.py` | PKCE auth, config, one-time token minting. |
| `pipe_test.py`, `check_login.py`, `export_playlists.py` | Phase-0 prover, auth check, library exporter. |
| `specs/*.json` | One spec per playlist (the 8 standing + test specs). |
| `rotation-history/*.json` | Per-lane memory of recent rotation picks. |
| `seed-playlists/*.txt` | Exported library snapshots — the taste-profile seed corpus. Read-only. |
| `taste-profile.md` | Jacob's taste. Claude maintains it; feedback log is additive. |
| `spotify-ai-dj-handoff.md` | **Project reference & history** — locked decisions, dead ends, phase records, hard-won facts. |
| `CHANGELOG.md` | Running record of notable changes, newest first. |
| `apple-music-port.md` | Deferred plan for an Apple Music delivery layer. |
| `his-version-planning/` | Planning docs for the brother's copy of the project (not built). |

## Repo hygiene

- `client_id` is fine in config; there is no client secret with PKCE. **Token cache file must be gitignored.** The refresh token and API key live only in GitHub secrets.
- Dead ends and corrections get recorded in the handoff doc, never deleted.
- Notable session work gets a dated entry in `CHANGELOG.md`.

## Git workflow

- **Work lands on `main`.** This is a solo personal project — no PR review flow. When a session starts on a designated feature branch (Claude Code on the web does this automatically), merge the work to `main` and push there rather than leaving it stranded on a branch or opening a PR. Don't push to long-lived side branches.
- Commit with clear, plain-language messages. Keep the token cache and any secrets out of history (gitignored).

## Reference

Full history — locked decisions, dead ends, API reality check, phase records with
acceptance tests, and the hard-won operational/technical facts: `spotify-ai-dj-handoff.md`.
Interview answers / operating decisions (naming, visibility, explicit content,
misses, standing playlists): handoff Section 10.
