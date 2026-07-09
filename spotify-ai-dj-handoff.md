# Spotify AI DJ — Project Handoff & Phased Plan

**Project:** Personal AI playlist curator ("ai-dj") — Claude curates, Spotify delivers, official app plays
**Owner:** Jacob (architect, SAI — coding novice, strong domain knowledge)
**Execution environment:** Claude Code, Windows (Dell Precision 5510)
**Status:** Phase 0 PASS. Phase 1 COMPLETE (taste-profile v1.0 locked). **Phase 2 PASS** — the resolver ran in GitHub Actions and scored 25/25 on the acceptance spec (2026-07-09). Next action is first real use: build the 7 standing playlists. **See Section 11 — it's the resume-here checkpoint and has the exact next steps.**
**Last updated:** 2026-07-09

---

## 1. Functional Spec

Jacob wants a Pandora/Apple Music replacement where an AI generates playlists tailored to his taste, at zero/near-zero marginal cost. He is cancelling Apple Music. He has Spotify Premium through a Duo plan shared with his brother (his own account — no shared-login issues).

**The system:**
- Jacob prompts Claude Code with a mood, activity, era, or vibe
- Claude generates a tracklist from its own music knowledge, informed by a persistent taste profile
- A Python script resolves tracks against Spotify's catalog and creates/updates a playlist on Jacob's account
- Jacob plays the playlist in the official Spotify app (iPhone or desktop) — full Premium quality, offline downloads, no ads
- Feedback ("skip the ambient stuff", "more like track 4") updates the taste profile for next time

**Explicitly NOT in scope:** playing audio, a custom playback UI, real-time "radio" that reacts per-song, anything requiring a server.

---

## 2. Locked Architecture Decisions — do not relitigate

| Decision | Choice | Rationale |
|---|---|---|
| Music source | Spotify catalog via Jacob's own Premium account (Duo) | Feb 2026: Dev Mode apps *require* the owner to hold active Premium. Jacob already pays for it. Free-account route is dead as of Feb 2026. |
| Playback | Official Spotify apps | Jacob approved app-frontend/custom-backend split. Sidesteps all iOS PWA audio flakiness. Playlists sync automatically. |
| Curation engine | Claude Code session (interactive) | $0 marginal cost on existing subscription. Anthropic API backend = future upgrade path (Section 8), not v1. |
| Language | Python 3, minimal deps | Novice-friendly; matches Jacob's other projects (Pi alarm plan, terrain scripts). |
| Auth flow | Authorization Code with PKCE | No client secret to protect — safest pattern for a novice's local script. Token cached locally, gitignored, auto-refreshed. |
| Where it runs | Local script on Dell laptop, run on demand by Claude Code | No server exists (no Pi purchased yet — confirmed 2026-07-08). No hosting cost. No scheduler needed for on-demand playlists. |
| Taste memory | `taste-profile.md` in repo, maintained by Claude | Plain-text, human-readable, survives across sessions, versioned in Git. |
| Spotify's role | Catalog search + playlist CRUD **only** | All discovery endpoints removed for new Dev Mode apps (see Section 3). Claude does 100% of curation. |

---

## 3. API Reality Check (verified 2026-07-08 against Spotify's Feb 2026 migration guide)

This section exists because Spotify has repeatedly cut Dev Mode capabilities (Nov 2024, then Feb 2026). The implementing Claude must treat this as ground truth and **re-verify against current docs in Phase 0** — the pattern suggests further cuts are possible.

> **Re-verified 2026-07-09** against Spotify's Feb-2026 migration guide, changelog, and the 2026-02-06 developer blog post. Section 3 holds — the load-bearing endpoints (PKCE auth, `GET /search` max 10, `POST /me/playlists`, playlist item add) are all still available. Drift found, none of it blocking:
> - **Timeline:** the endpoint cuts for existing apps went fully live **2026-03-09**; the Premium requirement + 5-user cap have applied since **2026-02-11**. No grace period remains — we build against the fully-restricted API.
> - **Saved/Liked tracks moved:** the old `/me/tracks` surface is consolidated into `GET /me/library` (+ `GET /me/library/contains`, `PUT`/`DELETE /me/library`). Affects Phase 1 taste-seed reading only, not the Phase 0 pipe.
> - **Explicit filtering effectively unavailable:** the `explicit_content` profile field was removed. Moot given the "allow everything" decision (Section 10) — and it retroactively validates that choice.
> - **More fields stripped from responses:** `followers`, `external_ids`, `linked_from` (on top of the already-noted `popularity`, `label`, `product`, `email`, `country`). The resolver needs none of them — search returns URI + name + artist, which is sufficient.

**Available and load-bearing:**
- `GET /search` — resolve tracks. **Limit max is 10 per request** (was 50); default 5. Paginate with `offset`.
- `POST /me/playlists` — create playlist (the old `POST /users/{id}/playlists` is removed)
- `POST /playlists/{id}/items` — add tracks (renamed from `/tracks`; **confirmed live 2026-07-09** by the Phase 0 pipe test — `/items` returned 201, not `/tracks`)
- `PUT /playlists/{id}/items`, `DELETE /playlists/{id}/items` — reorder/replace/remove
- `GET /me/playlists`, `GET /playlists/{id}/items` — read own playlists (items only returned for playlists the user owns/collaborates on)
- `GET /me` — profile (note: `product`, `email`, `country` fields removed)
- `GET /tracks/{id}`, `GET /artists/{id}`, `GET /albums/{id}` — individual fetches only

**Removed — never call, never debug:**
- `/recommendations`, `/audio-features`, `/audio-analysis` (Nov 2024)
- `/artists/{id}/related-artists`, `/artists/{id}/top-tracks` (removed for new apps)
- All batch fetches: `GET /tracks?ids=`, `GET /artists?ids=`, `GET /albums?ids=` — fetch individually
- `/browse/new-releases`, `/browse/categories`
- Other users' profiles/playlists (`GET /users/{id}/*`)
- `popularity` field on tracks/artists/albums, `label` on albums — gone from responses

**Account/app constraints:**
- 1 Client ID per developer, 5 users per app (fine — this app has 1 user)
- Owner must hold active Premium; app stops working if it lapses (Jacob's Duo covers this — **note: if the Duo plan ever changes, this project has a dependency on it**)
- Dev Mode rate limits are modest; the per-track individual fetches + 10-result search pages mean the script should throttle politely (small sleep between calls) and batch its work per playlist, not per keystroke

---

## 4. Dead Ends & Rejected Options — recorded, never deleted

| Option | Why rejected |
|---|---|
| Navidrome/Jellyfin self-hosted library | No Pi owned yet; Jacob has no music library and doesn't want to buy one — the whole point is avoiding new spend. Revisit if he ever buys a Pi AND builds a library. |
| Royalty-free catalogs (Jamendo, FMA) as primary source | Zero overlap with commercial catalogs by definition — royalty-free artists never signed label deals. Viable only as a *discovery side-quest*, not a replacement. |
| Free Spotify account as source | Killed by Feb 2026 Premium requirement for Dev Mode apps. Was also degraded by mobile shuffle-mode limits. |
| Piggybacking brother's account | Single concurrent stream = fighting over playback; Jacob's listening would pollute brother's algorithm (tastes differ significantly); against ToS with API credentials attached; and unnecessary — Jacob has his own Premium via Duo. |
| Custom PWA for playback | iOS background-audio flakiness in installed PWAs; Web Playback SDK effectively out of reach for new apps post-2025 access changes. Official app is strictly better here. |
| Spotify's recommendation engine as the brain | Endpoints removed Nov 2024. Claude's music knowledge replaces it — arguably an upgrade (steerable by natural language, explains its choices). |
| Anthropic API as v1 curation backend | Works, but costs real (if small) money per playlist and adds key management for a novice. Deferred to Section 8. |

---

## 5. Phased Plan

**Phase ordering rule:** riskiest unknown first. The riskiest unknown is whether a brand-new Dev Mode app (post-Feb 2026 restrictions) can complete the full auth → search → create → populate round-trip. Prove that before building anything nice.

### Phase 0 — Preserve seed data + prove the pipe (riskiest unknown)

**Before anything else:**
1. **Export Apple Music playlists NOW, before cancelling.** Minimum viable: share links or manual artist–title lists pasted into `seed-playlists/` as text files. These are the taste-profile seed corpus and are unrecoverable after cancellation.
2. Create the Spotify app at developer.spotify.com (Web API use case). Record Client ID. Set redirect URI to `http://127.0.0.1:<port>/callback` (Spotify no longer allows `localhost` literal in new redirect URIs — use the loopback IP; verify current rules).
3. **Re-verify Section 3 against current Spotify docs** — flag any drift to Jacob before proceeding.

**Build:** one bare-bones script: PKCE auth (opens browser, catches callback locally, caches token) → search one hardcoded track → create a playlist named "AI DJ — pipe test" → add the track.

**Acceptance test:** playlist appears in Jacob's Spotify iPhone app with the correct track, within a minute, without touching the Spotify UI. Token refresh works on a second run a day later without re-login.

**Result (2026-07-09):** Round-trip **PASS**. `pipe_test.py` completed auth → search → create → add on Jacob's Dell (Windows, Python 3.14.6); the "AI DJ — pipe test" playlist appeared in his phone's Spotify app with the Nujabes track. Confirmed the add endpoint is `/items`. **Durability half still pending** — the next-day auto-refresh (no re-login) is verified by running `check_login.py` after the access token has expired (>1h / next day). Once that passes without opening a browser, Phase 0 is fully closed.

**If this phase fails** (e.g., Spotify has restricted app creation further): STOP. The fallback conversation is Section 8, option C.

### Phase 1 — Taste profile from seed data

Claude reads the exported Apple Music playlists and interviews Jacob on gaps (draft-first-then-interview pattern): favorite artists vs. incidental tracks, moods he actually queues up, hard nos. Output: `taste-profile.md` — genres, anchor artists, sonic descriptors, context buckets (work focus / cooking / driving I-70), and an explicit do-not-play list.

**Acceptance test:** Jacob reads the profile and agrees it's him. No code in this phase.

**Result (2026-07-09): PASS.** `taste-profile.md` locked at v1.0; Jacob approved ("great profile, no notes"). Built from Liked Songs, ~15k history, all 19 labeled playlists, and ~10 recent Apple adds, across two interview rounds. Key outcomes: signal priority is *likes > labeled playlists* (Jacob curates by liking, not playlisting); screamo ceiling = Of Mice & Men; focus lane = lo-fi/trip hop/downtempo (soft vocals OK); country is a broad go-to; 7 standing playlists approved (**AI DJ — Chill · Hype · Heavier · Summer · Workout · Country · Focus**).

### Phase 2 — The resolver script (`push_playlist.py`)

Input: a JSON or plain-text tracklist (artist – title per line). For each track: search Spotify (respecting the 10-result page cap), pick the best match (exact-ish artist+title match; prefer album version over live/remix unless requested), collect URIs, create the playlist with a supplied name/description, add tracks in order. Output a **miss report**: tracks not found or low-confidence matches, printed clearly for Claude to substitute.

Plain-language explanation required for: what PKCE is doing, what a URI vs. ID is, how the matcher decides, why we sleep between requests.

**Acceptance test:** a 25-track list with 2 deliberately misspelled entries produces a playlist with ≥20 correct tracks and a miss report naming the failures. Live/karaoke/cover junk matches < 2.

**Result (2026-07-09): PASS (exceeded).** `push_playlist.py` ran in GitHub Actions (run #2, `29020947104`) against `specs/resolver-test.json` and scored **25/25 matched, all confident, 0 weak, 0 missed.** The fuzzy matcher auto-corrected both deliberate typos (`Imagin Dragons - Radioactve` → Imagine Dragons - Radioactive; `Twenty One Piolts - Stresed Out` → Twenty One Pilots - Stressed Out). No live/karaoke/cover junk. *Final human check still owed:* Jacob eyeballs the "AI DJ — resolver test" playlist on his phone to confirm the track versions are right.

### Phase 3 — The DJ loop as a Claude Code skill/command

Codify the loop so any session can run it: read `taste-profile.md` → generate tracklist for the prompt → run resolver → handle misses with substitutions → confirm. Add an `update` mode (replace an existing playlist's items rather than creating a new one) for the standing "AI DJ" playlists (see Section 10). Note: the five source playlists Jacob named are **read-only seeds**, not update targets — the update targets are the AI-authored versions I create.

**Acceptance test:** cold session, one prompt ("hour-long Sunday cooking playlist, upbeat but not frantic"), playlist on the phone in one pass with ≤2 manual interventions.

### Phase 4 — Feedback + taste evolution

A lightweight convention: Jacob reports reactions in plain language; Claude appends dated adjustments to `taste-profile.md` (never silently rewrites history — additive log section). Optional: a `promote` command that copies loved tracks into a permanent "AI DJ Gold" playlist.

**Acceptance test:** after two feedback rounds, a regenerated playlist visibly reflects the corrections.

### Phase 5 (optional) — Discovery mode

Claude proposes tracks/artists *outside* the profile deliberately (adjacent genres, deep cuts, the East Asian ambient/jazz territory Jacob gravitates toward aesthetically). Marked as experiments; feedback feeds Phase 4. This replaces — and out-explains — Spotify's dead recommendation engine.

---

## 6. Out of Scope

- Playing audio anywhere in this codebase
- Scheduling/automation (no daily auto-playlists in v1 — no always-on machine exists)
- Multi-user anything
- Scraping Spotify or any workaround for removed endpoints
- Audio-feature analysis via third-party APIs (RapidAPI resellers exist; cost + reliability not worth it for v1)

## 7. Fail-loud defaults

Every script failure prints what failed, which track/call, and the HTTP status in plain English. No silent skips: a track that can't be resolved goes in the miss report, never quietly dropped. Auth failures explain whether it's an expired token (auto-fix) or a revoked app (manual fix, with steps).

## 8. Future upgrade paths (documented, not planned)

- **A. Anthropic API backend:** replace the interactive Claude Code session with a script calling the Messages API — enables one-command playlists outside Code sessions. Costs per-call; needs API key management. Sensible once the loop is proven.
- **B. Web front-end:** a small local page ("give me a vibe" text box) driving option A. Only worth it if the CLI loop feels clunky in practice.
- **C. Fallback if Spotify closes Dev Mode further:** revisit the self-hosted route (Navidrome + purchased library + future Pi) or Apple MusicKit ($99/yr developer account — Jacob prefers Apple's artist treatment, so this is not absurd if he'd otherwise return to an Apple Music subscription anyway).

## 9. Interview the implementing Claude must run before writing any code

1. Have you exported your Apple Music playlists yet? (If no — stop, do that first.)
2. Confirm: still on the Duo plan, own login works on developer.spotify.com?
3. Playlist naming convention preference? (e.g., "AI DJ — Sunday Cooking" prefix vs. bare names)
4. Default playlist visibility: private or public?
5. Explicit-content filter: allow everything, or filter?
6. When a track can't be found: substitute automatically with a Claude-chosen alternative, or always ask?
7. Standing playlists you already know you want (work focus, cooking, driving)? These become the Phase 3 update-mode targets.
8. Python installed on the Dell yet? Which version? (Determines whether Phase 0 starts with environment setup.)

---

## 10. Operating Decisions (interview answers, locked 2026-07-08)

Answers to the Section 9 interview. These are locked — do not relitigate.

| Question | Decision | Notes |
|---|---|---|
| Apple Music export | **Done** — playlists already live on Spotify | Seed-data risk retired. |
| Duo plan + dev portal login | **Confirmed working** | Can log into developer.spotify.com with the Duo account. |
| Naming convention | **`"AI DJ — {name}"` prefix** | e.g. "AI DJ — Sunday Cooking". Groups all authored playlists together. |
| Visibility | **Public** | Playlists appear on Jacob's Spotify profile. |
| Explicit content | **Allow everything** | No clean-version filtering; match the intended track. |
| Missed tracks | **Auto-substitute, silent** | Pick a close alternative and move on. No miss report needed for substitutions. (Still fail-loud on hard errors per Section 7 — a *silent substitution* is not a *silent drop*: every intended slot gets filled, but Jacob doesn't need a per-swap changelog.) |
| Standing playlists | **All 5 sources are read-only seeds** | Liked Songs, Your All-Time Top Songs, Lofi Cafe, 80s Rock, Trip Hop. I do NOT write to any of them. Instead I create/maintain AI-authored counterparts (below). |
| Python on run machine | **Not on Dell yet; will install** | Python 3.14.6 exists on Jacob's work desktop, but the Dell is home base. ~5-min install, walk through in Phase 0. Confirm `requests` supports 3.14. |

**Standing "AI DJ" playlists to build (Phase 3 update-mode targets):**
- `AI DJ — Liked Songs` (inspired by the Saved Tracks library, read as a taste seed)
- `AI DJ — Heavy Rotation` (counterpart to "Your All-Time Top Songs"; Spotify's own is Spotify-generated and not writable)
- `AI DJ — Lofi Cafe`
- `AI DJ — 80s Rock`
- `AI DJ — Trip Hop`

**Why "read-only seeds":** Liked Songs is a hand-curated library (a different API surface from playlists) — having a tool overwrite it is too destructive to risk. "Your All-Time Top Songs" is Spotify-generated and not user-editable, and leans on `/me/top/*` endpoints that may have been cut (verify in Phase 0). Both are safer as inputs I learn from than as things I manage.

### Runtime decision (extends Section 2 / Section 8-A)

**v1 runs locally on the Dell (Python install).** GitHub Actions is a valid — and attractive — hosting upgrade, but deferred, for two reasons:
1. **Initial PKCE consent is interactive** (browser login). Actions is headless, so the first auth must happen once on a real machine regardless; the resulting refresh token would then be stored as an encrypted GitHub secret for unattended runs.
2. **Actions front-loads complexity** (secrets, workflow files, a trigger mechanism to pass the tracklist in) onto an as-yet-unproven script. Phase 0's job is to prove the auth→search→create pipe with minimum moving parts.

**Design constraint carried forward:** write `push_playlist.py` **Actions-ready from the start** — token read from an environment variable, tracklist passed as a file, fully non-interactive execution. Migrating to Actions later becomes config (store secret + add workflow), not a rewrite. This is the concrete near-term form of Section 8-A.

---

## 11. Resume-Here Checkpoint (2026-07-09)

Snapshot of exactly where we stopped, so the next session starts cold with zero re-derivation. **Read this first.**

> **This checkpoint was refreshed 2026-07-09 after proving Phase 2 in the cloud.** Phases 0, 1, and 2 are all done. The Actions runtime is live and working end-to-end. **The next action is first real use — build the 7 standing playlists. See "DO THIS NEXT."**

### Where we are
- **Phase 0 — PASS (round-trip).** `pipe_test.py` did auth → search → create → add; playlist appeared on Jacob's phone. *Open (minor, non-blocking):* next-day refresh durability check via `check_login.py`.
- **Phase 1 — COMPLETE.** `taste-profile.md` **locked at v1.0**, Jacob approved ("great profile, no notes"). Built from all 19 labeled playlists + Liked Songs + ~10 recent Apple adds + 2 interview rounds.
- **Phase 2 — PASS (proven in Actions, 2026-07-09).** `push_playlist.py` ran against Jacob's real account via GitHub Actions (run `29020947104`) and scored **25/25 on `specs/resolver-test.json`** (all confident, 0 weak, 0 missed; both deliberate typos auto-corrected; no junk). The `SPOTIFY_REFRESH_TOKEN` secret is set and the Actions→Spotify auth path works headless. *Owed:* Jacob's phone-eyeball of the "AI DJ — resolver test" playlist.

### ⭐ DO THIS NEXT — first real use (build the 7 standing playlists)

The pipe is proven; now generate real tracklists and build the standing playlists. For each of the 7 (**Chill · Hype · Heavier · Summer · Workout · Country · Focus**):
1. Read `taste-profile.md` for what that bucket should contain.
2. Generate a tracklist and write it to `specs/<name>.json` (see the spec format in `push_playlist.py`'s header; `mode: "create"` first time, `"update"` thereafter).
3. Commit + push the spec to `main`.
4. Dispatch **`Build Playlist`** (`.github/workflows/build-playlist.yml`) with `spec = specs/<name>.json` via the GitHub MCP tool `actions_run_trigger` (ref `main`).
5. Read the run logs (`get_job_logs`); substitute any misses/weak matches in the spec and re-dispatch if needed.
6. Jacob eyeballs the result on his phone.

**Dispatch mechanics that are now known-good:** ref `main`, workflow file `build-playlist.yml`, input key `spec`. A healthy run reaches the "Build the playlist" step and prints the per-track match report + a summary line.

### The ongoing loop (how Claude drives this now)
Generate tracklist → write `specs/<name>.json` → commit+push to `main` → dispatch `Build Playlist` with that spec path → read logs → substitute misses, re-dispatch if needed. The playlist appears on Jacob's account. He does nothing.

### What's built and committed (all on `main`)
- `config.py` — Client ID, redirect URI, token-cache path, the 6 scopes. Env-overridable.
- `spotify_auth.py` — PKCE login, callback catcher, token cache, auto-refresh, **scope-aware**, **CI guard** (fails fast in Actions if the secret is missing instead of hanging). Uses `SPOTIFY_REFRESH_TOKEN` env var when set (the Actions path).
- `pipe_test.py` — Phase 0 prover. · `check_login.py` — no-side-effect auth check.
- `export_playlists.py` — read-only library dump → `seed-playlists/*.txt`.
- `seed-playlists/` — ALL 19 playlists populated + `liked-songs.txt` (1,214) + `top-tracks.txt` (~15k) + `recent-apple-adds.txt` (10).
- `taste-profile.md` — **v1.0, locked.**
- `push_playlist.py` — the resolver (spec JSON → search/match/create-or-update → report).
- `specs/resolver-test.json` — 25-track acceptance-test spec (2 deliberate typos).
- `print_refresh_token.py` (reads Dell cache) and `get_token.py` (stdlib-only, any machine) — both mint the secret value.
- `.github/workflows/build-playlist.yml` — the Actions runtime.

### Backlog (do at END of build, per Jacob's request)
- **Save-to-Liked-Songs feature:** add `user-library-modify` scope + a helper so Claude can save tracks into Jacob's Liked Songs directly. He'll grant that permission later.
- **Matcher blind spot (found building Chill):** a track can match as *confident* while being the wrong *version*. Seen: "Hozier - Cherry Wine" resolved to "Andrew Hozier-Byrne, Arlo Vega - Cherry Wine (Arr. for Guitar)" — a guitar arrangement — because "arr."/"guitar" aren't in `BAD_VERSION_WORDS` and the secondary-artist credit still scored as Hozier. Consider: add arrangement/rendition words to the penalty list, and/or penalize when the candidate has an extra lead artist the query didn't name. **Mitigation until then: always eyeball the matched titles in the run log, not just the match counts.**

### The 7 standing playlists (build progress)
**AI DJ — Chill · Hype · Heavier · Summer · Workout · Country · Focus.** Everything else (nostalgia, seasonal, Taylor) stays on-demand. See `taste-profile.md` for what each contains.
**ALL 7 BUILT ✅ (2026-07-09).** Each is `specs/<name>.json`, 22 tracks, all now `mode: "update"` (so re-runs replace in place). Per-playlist:
- **Chill** — 22/22 confident. Shook out the full loop (2 substitutions, then update-mode re-run).
- **Hype** — 22/22 in playlist. (mgk credit tidied in spec.)
- **Heavier** — 22/22 confident. Stayed under the OM&M screamo ceiling.
- **Summer** — 22/22 confident.
- **Workout** — 22/22 in playlist. (mgk credit tidied in spec.)
- **Country** — 22/22 confident. ("One Beer" resolves to the HIXTAPE original — correct.)
- **Focus** — 22/22, after one substitution: "Idealism - Both of Us" resolved to the wrong song → swapped to "Emancipator - Greenland" and re-run in update mode.

**Ongoing maintenance:** edit the relevant `specs/<name>.json`, commit to `main`, dispatch `Build Playlist` with that spec (already `update` mode → replaces in place). Always eyeball matched *titles* in the log, not just counts.

### Jacob's TODO
1. ~~Set the `SPOTIFY_REFRESH_TOKEN` secret~~ **DONE** (2026-07-09).
2. ~~Enable GitHub Actions billing~~ **DONE** — added a payment method + $10 Actions spending limit (2026-07-09). This is what unblocked the runners (see hard-won facts).
3. *(Minor)* run `check_login.py` once to close Phase 0's durability half.
4. *(Optional)* delete the "AI DJ — pipe test" / "AI DJ — resolver test" playlists later.

### Environment facts (don't rediscover)
- **Runtime is GitHub Actions**, triggered by Claude via GitHub MCP. Auth = `SPOTIFY_REFRESH_TOKEN` secret. Actions runners CAN reach Spotify.
- **The cloud Code sandbox's egress policy BLOCKS `accounts.spotify.com` (403).** So *this Claude cannot do token exchange or run `push_playlist.py` directly* — anything touching Spotify must run on Jacob's machine or in Actions. (This is why the runtime is Actions.)
- Jacob's Dell: Windows, PowerShell, Python 3.14.6, git 2.55, repo at `C:\Users\jskra\Documents\music-player`, git identity set, push works via browser auth (no passwords). `.spotify_token.json` cached there with full scopes.
- All work lands on `main`.

### Hard-won operational facts (don't relearn these)
- **GitHub Actions needs billing set up even for a public repo.** Before a payment method + spending limit existed on the account, dispatched runs were *accepted* (workflow `active`, dispatch returned 204) but **no hosted runner ever attached** — `runner_id` stayed `0`, the job sat `queued`, and GitHub auto-cancelled it at the ~15-minute queue timeout. Symptom to recognize: dispatch works, workflow is active, secret is set, but the job never starts and dies at 15 min. Fix was adding a payment method + a $10 Actions spending limit at `github.com/settings/billing`; the very next dispatch got a runner within ~6 min and ran green.
- **`github.com/settings/actions` 404s for this account** — not a problem; account-level Actions controls live under billing, not that path.

### Hard-won technical facts (don't relearn these)
- **Add-to-playlist endpoint is `/items`** (confirmed). `PUT /playlists/{id}/items` replaces; `POST` appends (batch by 100).
- **Playlist `/items` wraps the track under `"item"`**; the old `"track"` key is now a boolean flag. Saved/Liked tracks still wrap under `"track"`. Top-tracks are bare track objects.
- **`/me/top/tracks` returns ~15k tracks** (deep history, not a top-50).
- **Taste essentials:** signal priority = *likes > labeled playlists* (Jacob curates by liking); screamo ceiling = Of Mice & Men (melodic-with-screams OK); focus lane = lo-fi/trip hop/downtempo (soft vocals OK); country is a broad go-to; hard/technical rap out (Hopsin, Krizz Kaliko, sKitz Kraven, Tech N9ne), melodic/emo rap OK. **Endel was removed** — it topped raw history but Jacob doesn't use it; not a taste signal.

---

**Jacob — standing reminder:** save copies of this doc and the CLAUDE.md to Obsidian for offline storage, in addition to committing them to the Git repo.
