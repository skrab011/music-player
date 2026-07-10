# Changelog

A running record of notable changes to the AI DJ project. Newest first.

---

## 2026-07-10 — New on-demand playlist: AI DJ — Soft Morning

Jacob asked for a soft, moody playlist to sleep to on the bus ride to work.
Built as a **new** on-demand playlist (distinct from the standing Soft & Moody),
leaning soft bedroom-pop at low activation — the gentlest end of the
Billie / Clairo / girl in red neighborhood, ~20 tracks for a ~60-minute ride.

- New spec `specs/soft-morning.json`; built via `Build Playlist`.
- Resolver confidently mismatched `Alec Benjamin - Water` → "Water Fountain";
  caught it on the title eyeball and swapped to "Let Me Down Slowly".
- Playlist: https://open.spotify.com/playlist/1PAinWGQQGwAL5Im1P18Y9
  (20/20 confident matches, 0 weak, 0 missed).

## 2026-07-10 — Documentation consolidation

The docs had drifted badly from reality (the README still said "not yet built").
One pass to make them truthful and give each doc a single job:

- **`spotify-ai-dj-CLAUDE.md` → `CLAUDE.md`** (renamed so Claude Code auto-loads
  it) and rewritten as the lean **operator's manual**: current state, the API
  rules, how to run the on-demand loop and maintain standing playlists, how the
  rotation works, environment facts, and a repo map.
- **`README.md`** rewritten to describe the built-and-running system (8 standing
  playlists, weekly rotation, Actions runtime) instead of the pre-build plan.
- **`spotify-ai-dj-handoff.md`** reframed as the **project reference & history**.
  Superseded decisions annotated in place, never deleted: §2 "runs locally on the
  Dell" → GitHub Actions; §6 "no scheduling/automation" → the weekly rotation.
  Phase 3 marked passed-in-practice, Phase 5 marked live as the rotation. §11
  refreshed from "resume-here / build the 7" to a current-state checkpoint
  covering the rotation machinery and the Soft & Moody 8th standing playlist.
- **`taste-profile.md`** — status touch-ups only (standing playlists marked
  built + rotating; Soft & Moody noted; dated status line in the feedback log).
  No taste content changed.
- **`his-version-planning/`** left as-is per Jacob, except the two references to
  the old `spotify-ai-dj-CLAUDE.md` filename, updated so the rename doesn't
  leave dead pointers.

Doc roles going forward: `CLAUDE.md` = how to operate (auto-loaded every
session) · `spotify-ai-dj-handoff.md` = decisions, dead ends, history ·
`CHANGELOG.md` = what happened, session by session.

---

## 2026-07-10 — Custom curation, weekly discovery rotation, and brother's-version planning

A single evening session. Three threads: a one-off custom playlist that became
a standing one, a new weekly auto-rotation engine for the standing playlists,
and planning docs for sharing the project with Jacob's brother.

### Added — "AI DJ — Soft & Moody" custom curation
- **`specs/soft-moody.json`** — a soft, moody, cinematic playlist anchored on
  Billie Eilish (moody era) and **Ella Red** (North Texas alt-pop; "I Like You
  Best"), filling the dream-pop / bedroom-pop neighborhood between them, weighted
  toward the chill lane of `taste-profile.md`.
- Built on Spotify: 24/24 tracks matched cleanly on the first run.
- **Promoted to a standing playlist** — flipped from `create` to `update` mode so
  future refreshes land in place (same URL/followers) instead of spawning a copy.
  It is a custom lane, separate from the 7 standing playlists.

### Added — Weekly discovery rotation for the 7 standing playlists
The 7 "AI DJ —" playlists were static (no schedule; fixed tracklists). They now
rotate themselves weekly, functioning as a discovery avenue.

- **`generate_rotations.py`** — each week, asks Claude for a fresh batch of
  "adjacent deep cuts" per lane (songs clearly in-taste but likely unheard),
  guided by `taste-profile.md` and its Do-Not-Play rules. Uses structured output
  (strict JSON schema) so it returns a clean tracklist. Writes the 7 specs and
  records the picks to history.
  - Model configurable via `ANTHROPIC_MODEL` (default `claude-opus-4-8`;
    `claude-haiku-4-5` for near-free).
  - `TRACKS_PER_LANE = 24`, `HISTORY_WEEKS = 8`.
- **`rotation-history/<lane>.json`** — per-lane memory of recent weeks' picks,
  fed back into the prompt as "don't repeat these" so discovery keeps moving.
  Seeded on the first run (all 7 lanes).
- **`.github/workflows/rotate-playlists.yml`** — the weekly job:
  generate → build all 7 via `push_playlist.py` → commit refreshed specs +
  history back to `main`. Runs **Fridays 18:00 UTC** (new-music-Friday releases
  are live by then); also manually triggerable (`workflow_dispatch`).
- **`requirements.txt`** — added `anthropic>=0.40`.
- **New repo secret required:** `ANTHROPIC_API_KEY` (recommended: a dedicated key
  in a spend-capped Anthropic Workspace).

**First run verified** (manual trigger): all 7 lanes generated, built, and the
history committed back. Representative match rates — Country 24/24, Focus 23/24,
Summer 23/24, Workout 20/24. Cost for the run: **~$0.26**.

Design decisions (Jacob's calls):
- **All 7 rotate weekly**, overwriting freely — no "keepers" playlist. Rationale:
  Liked Songs *is* the keeper mechanism. Discovery → Like the winners → they enter
  Liked Songs → which the taste profile already treats as the #1 signal → sharper
  discovery next week.
- **Discovery dial: "adjacent deep cuts"** (safe, high-hit-rate discovery).
- Accepted tradeoffs (no action taken): the automated run has no human to
  substitute misses, so ~1–2 "weak" resolver guesses slip in per lane; and the
  Workout lane can lean up against the screamo ceiling. Both deemed fine.

### Added — Planning for the brother's version (`his-version-planning/`)
Not built — planning only, for a future session to design a copy of the project
for Jacob's brother.
- **`his-version-planning/sharing-options.md`** — the full menu: what's portable
  vs. personal, the AI/bot options, the three curation models (no-AI pool sampler,
  scheduled API generation, on-demand), and the leading direction.
- **`his-version-planning/handoff.md`** — a self-contained brief for a fresh
  planning session. Leading direction: **a messaging bot (Telegram or SMS) on a
  cheap model (Haiku), powered by Jacob's spend-capped API key held server-side**,
  so the brother chats to get playlists with no subscription (~$1–2/mo). The
  consumer Claude app can't take an API key; a bot can.

### Repo / ops
- Merged the session branch to **`main`** and continued work there (per the solo
  project's workflow).

### Commit trail
```
3e60064  Add custom Soft & Moody curation (Billie Eilish / Ella Red neighborhood)
7056e75  Promote Soft & Moody to a standing playlist (update mode)
f4fddb6  Add sharing-options.md — scratch notes on sharing the AI DJ
75684ac  Move brother's-version planning into his-version-planning/ + add handoff
bd41ca2  Add weekly discovery rotation for the 7 standing playlists
c228677  Run weekly rotation Fridays 18:00 UTC (new-music-Friday releases)
3e9eb6e  Weekly rotation: refresh standing playlists (2026-07-10)   [rotation bot]
```
