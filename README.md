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

## How it works

```
You: "90 minutes of focus music, instrumental, some Nujabes energy"
        │
        ▼
Claude  ── reads taste-profile.md, generates a tracklist (artist – title)
        │
        ▼
push_playlist.py ── searches Spotify for each track, picks best matches,
        │            auto-substitutes anything missing, creates/updates the playlist
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

## Status

**Scoped and planned — not yet built.** Next up is Phase 0 (prove the full
auth → search → create → populate round-trip works), which needs a machine at
home. See the roadmap below.

## What's in this repo

| File | What it is |
|---|---|
| `README.md` | This file. |
| `spotify-ai-dj-CLAUDE.md` | Working guide for Claude: what the project is, how to behave, the API rules. |
| `spotify-ai-dj-handoff.md` | The full plan — architecture decisions, dead ends, phased roadmap, acceptance tests, and the locked operating decisions (Section 10). |

Coming as the project is built:
- `push_playlist.py` — the resolver/delivery script
- `taste-profile.md` — the persistent record of your taste (Claude maintains it)
- a token cache file — your Spotify login, **gitignored**, never committed

## Key decisions (the short version)

- **Playlist naming:** `AI DJ — {name}` prefix, so they group together in your library
- **Visibility:** public
- **Explicit content:** allowed (no clean-version filtering)
- **Missing tracks:** auto-substitute a close alternative silently — every slot gets filled, nothing is dropped
- **Standing playlists:** five source playlists (Liked Songs, All-Time Top, Lofi Cafe, 80s Rock, Trip Hop) are **read-only inspiration** — the tool builds its own "AI DJ" versions rather than overwriting them
- **Where it runs:** locally, on demand — no server, no hosting, no always-on machine. Written to be moved to GitHub Actions later with config-only changes.

Full reasoning for each lives in `spotify-ai-dj-handoff.md` Section 10.

## Roadmap

| Phase | Goal |
|---|---|
| **0** | Prove the pipe: PKCE login → search a track → create a test playlist → add it. Riskiest unknown first. |
| **1** | Build `taste-profile.md` from the existing playlists plus a short interview. |
| **2** | Build `push_playlist.py` — resolve a tracklist, match tracks, auto-substitute misses. |
| **3** | Codify the full DJ loop as a repeatable command, with an update mode for standing playlists. |
| **4** | Feedback loop — plain-language reactions evolve the taste profile over time. |
| **5** *(optional)* | Discovery mode — deliberate picks outside the profile, marked as experiments. |

## Stack

- **Python 3**, minimal dependencies (`requests`)
- **Auth:** Spotify Authorization Code with PKCE (no secret to protect), token cached locally and auto-refreshed
- **Curation:** an interactive Claude Code session — $0 marginal cost on an existing subscription
- **Playback:** the official Spotify apps — this project delivers playlists, it doesn't play them

## Requirements

- A Spotify Premium account (required for this kind of app as of Feb 2026)
- A free Spotify developer app (Client ID only — no paid tier)
- Python 3 on the machine you run it from
- A Claude Code session to do the curating
