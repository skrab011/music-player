# AI DJ — a personal AI playlist curator

**Claude curates, Spotify delivers, the official Spotify app plays.**

A zero/near-zero-cost replacement for a music-streaming recommendation service.
You describe a mood, activity, era, or vibe; Claude generates a tracklist from
its own music knowledge (guided by a saved taste profile); a small Python script
resolves those tracks against Spotify's catalog and creates or updates a playlist
on your own account. You listen in the official Spotify app — full Premium
quality, offline downloads, no ads.

This project **never plays audio itself**. It has no UI, no server, and stores
no music. It's a curation-and-delivery pipe, nothing more.

---

## Status: built and running

- **8 standing "AI DJ —" playlists** live on the account: Chill · Hype ·
  Heavier · Summer · Workout · Country · Focus, plus the custom **Soft & Moody**.
- **Weekly discovery rotation:** every Friday (18:00 UTC, after new-music-Friday
  releases land) a GitHub Actions job asks Claude for a fresh batch of "adjacent
  deep cuts" per lane and rebuilds the 7 rotating playlists in place. Per-lane
  history is fed back into the prompt so picks don't repeat. Cost: ~$0.26/run.
- **On-demand playlists** any time, by asking Claude in a Code session.
- The keeper mechanism is Spotify itself: Like the discovery winners → Liked
  Songs is the taste profile's #1 signal → sharper curation next week.

## How it works

```
You: "90 minutes of focus music, instrumental, some Nujabes energy"
        │
        ▼
Claude  ── reads taste-profile.md, generates a tracklist,
        │  writes it to specs/<name>.json, commits it
        ▼
GitHub Actions ── "Build Playlist" workflow runs push_playlist.py:
        │          searches Spotify for each track, picks best matches,
        │          creates or updates the playlist
        ▼
Spotify ── playlist appears on your account
        │
        ▼
You    ── press play in the Spotify app (phone or desktop)
```

Feedback in plain language ("less ambient", "more like track 4") updates the
taste profile, so it gets more *you* over time.

## The one fact that shapes everything

**Spotify's API is dumb catalog plumbing now — not a recommendation brain.**
After Spotify's Nov-2024 and Feb-2026 changes, apps like this one only get:

- **Catalog search** — turn "Artist – Title" into a playable track
- **Playlist create/update** — build and fill the playlist

Everything Spotify used to offer for *discovery* (recommendations, audio
features, related artists, top tracks, browse) is gone for this kind of app.
So **100% of the curation intelligence comes from Claude.** That's arguably an
upgrade: it's steerable in plain English and can explain its choices.

## What's in this repo

| Path | What it is |
|---|---|
| `README.md` | This file. |
| `CLAUDE.md` | The operator's manual — auto-loaded by Claude Code; how to run the loop today. |
| `spotify-ai-dj-handoff.md` | Project reference & history: locked decisions, dead ends, phase records, hard-won facts. |
| `CHANGELOG.md` | Running record of notable changes, newest first. |
| `taste-profile.md` | The persistent record of Jacob's taste (Claude maintains it). |
| `push_playlist.py` | The delivery engine: spec JSON → search/match → create-or-update playlist. |
| `generate_rotations.py` | The weekly rotation curator (Anthropic API → fresh specs for the 7 lanes). |
| `spotify_auth.py` · `config.py` · `get_token.py` · `print_refresh_token.py` | PKCE auth, config, one-time refresh-token minting. |
| `pipe_test.py` · `check_login.py` · `export_playlists.py` | Phase-0 prover, auth check, library exporter. |
| `specs/` | One JSON spec per playlist. |
| `rotation-history/` | Per-lane memory of recent rotation picks (anti-repetition). |
| `seed-playlists/` | Exported library snapshots — the taste-profile seed corpus. |
| `.github/workflows/` | `build-playlist.yml` (on-demand builds) and `rotate-playlists.yml` (weekly rotation). |
| `apple-music-port.md` | Deferred, ready-to-execute plan for an Apple Music delivery layer. |
| `his-version-planning/` | Planning docs for a copy of the project for Jacob's brother (not built). |

## Key decisions (the short version)

- **Playlist naming:** `AI DJ — {name}` prefix, so they group together in your library
- **Visibility:** public
- **Explicit content:** allowed (no clean-version filtering)
- **Missing tracks:** auto-substitute a close alternative — every slot gets filled, nothing is silently dropped
- **Source playlists are read-only inspiration** — the tool never overwrites Liked Songs or any hand-made playlist; it maintains its own "AI DJ —" playlists
- **Where it runs:** GitHub Actions — the cloud sandbox Claude works in can't reach Spotify, and no always-on machine exists. Claude dispatches workflows and reads the logs; delivery happens on the runners.

Full reasoning for each lives in `spotify-ai-dj-handoff.md` (Sections 2, 10, and 11).

## Stack

- **Python 3**, minimal dependencies (`requests`, plus `anthropic` for the rotation)
- **Auth:** Spotify Authorization Code with PKCE (no secret to protect); a refresh
  token minted once on a real machine lives in the `SPOTIFY_REFRESH_TOKEN` repo
  secret for headless Actions runs
- **Curation:** an interactive Claude Code session ($0 marginal cost on an existing
  subscription) for on-demand playlists; the Anthropic API (spend-capped key,
  `ANTHROPIC_API_KEY` secret) for the unattended weekly rotation
- **Playback:** the official Spotify apps — this project delivers playlists, it doesn't play them

## Requirements

- A Spotify Premium account (required for this kind of app as of Feb 2026)
- A free Spotify developer app (Client ID only — no paid tier)
- A GitHub repo with Actions enabled (billing set up — runners won't attach without it, even on a public repo)
- A Claude Code session to do the curating (plus an Anthropic API key if you want the weekly rotation)
