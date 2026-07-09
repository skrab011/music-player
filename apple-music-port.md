# Apple Music Port — Plan (deferred, not started)

**Status:** DEFERRED. Spotify remains the live pipeline. This doc is a ready-to-execute
plan for porting the AI DJ's *delivery layer* to Apple Music if/when Jacob decides the
sound quality + artist treatment justify the cost. Written 2026-07-09; verify the
Apple Music API details against current docs before implementing (Apple changes these
less often than Spotify, but check anyway).

**Decision recorded:** keep Spotify for now (works, ~$0 beyond the existing Duo Premium).
Revisit Apple Music only alongside — or in place of — a *resubscription* to Apple Music.

---

## 1. The cost reality (why this isn't $0)

There is **no free tier for the Apple Music API.** Two hard costs:

1. **Apple Developer Program — $99/year.** Required just to mint the developer token that
   every Apple Music API call needs. No dev-mode/free equivalent to Spotify.
   - *Silver lining:* this membership is not music-specific. It covers all iOS/macOS app
     development, TestFlight, and App Store distribution. If Jacob builds other Apple-platform
     things (Pi/phone apps, etc.), the $99 is shared overhead, not a pure music tax.
2. **An active Apple Music subscription** (the thing that was cancelled). Writing playlists into
   *your* library requires a **Music User Token**, which requires an active subscription.

So the real floor is **$99/yr developer + Apple Music sub**, not $99 flat. This is the whole
decision — the engineering below is the easy part.

---

## 2. What carries over vs. what changes

**The curation brain is platform-agnostic and transfers unchanged:**
- `taste-profile.md` — untouched.
- Claude generating tracklists from a prompt — untouched.
- The `specs/*.json` format (name, description, mode, tracks) — untouched.
- The fuzzy matcher in `push_playlist.py` (`_norm`, `_ratio`, `_score`, `_version_penalty`,
  thresholds) — **reused as-is.** Matching "Artist - Title" against catalog results is the
  same problem on either platform.
- The GitHub Actions runtime model (dispatch a spec → build in the cloud) — untouched.

**Only the delivery layer is Spotify-specific and needs a rewrite:**
- Auth module (`spotify_auth.py`) → new `apple_auth.py`.
- The HTTP calls in `push_playlist.py` (search + playlist create/add).
- The workflow's secrets.

Estimated effort: **~1 day**, most of it re-testing the auth handshake and the
library-playlist update semantics (see the gotcha in §6).

---

## 3. Auth — the real difference from Spotify

Spotify handed you one thing (a refresh token from a browser login). Apple splits auth in two:

### 3a. Developer token (machine-to-machine, fully scriptable)
- A **JWT signed with ES256** using a `.p8` private key you download from the Apple Developer
  portal. No browser, no user — the CI can generate this itself every run.
- **Header:** `{ "alg": "ES256", "kid": "<MUSICKIT_KEY_ID>" }`
- **Payload:** `{ "iss": "<TEAM_ID>", "iat": <now>, "exp": <now + up to 15777000s (~6 months)> }`
  - For MusicKit-JS use you also add an `origin` claim; not needed for server-side API calls.
- Sign with the `.p8`. In Python: `PyJWT` with the `cryptography` backend, or sign ES256 manually.
- **Refresh story:** trivial — just re-sign. Store the `.p8` (+ Key ID + Team ID) as secrets and
  mint a fresh token at the top of every run.

### 3b. Music User Token (acts on behalf of the user — needed for library writes)
- Obtained **once** via **MusicKit JS** in a browser: load a tiny local HTML page configured with
  your developer token, call `music.authorize()`, log in with the Apple Music account, and it
  returns the Music User Token (MUT). Copy it, store as a secret.
- This is the analog of `get_token.py` — a one-time, interactive bootstrap — but a small HTML
  page instead of a Python script (MusicKit JS is the only sanctioned way to get a MUT for web).
- **Refresh story — the weak spot:** there is **no clean server-side refresh** for the MUT.
  It's long-lived but can expire or be revoked; if it dies you redo the one-time browser step.
  (Contrast Spotify's clean OAuth refresh. Plan for the occasional manual re-auth.)

### 3c. Request headers
Every personalized/library call sends BOTH:
```
Authorization: Bearer <developer_token>
Music-User-Token: <music_user_token>
```
Catalog-only calls (search) need just the `Authorization` bearer.

---

## 4. One-time bootstrap checklist (Jacob, ~30–45 min)

1. Enroll in the **Apple Developer Program** ($99/yr) with the Apple ID tied to the Apple Music sub.
2. In the developer portal → **Certificates, Identifiers & Profiles → Keys → +**, create a key with
   **MusicKit** enabled. Download the **`.p8`** (one-time download — save it) and note the **Key ID**.
3. Note your **Team ID** (membership details).
4. Build a minimal **MusicKit-JS auth page** (single local `.html`, MusicKit v3): configure it with a
   dev token, click **Authorize**, copy the printed **Music User Token**. (Reference page to be added
   under `tools/` when we implement.)
5. Add the four secrets to GitHub (see §7).

---

## 5. Endpoint mapping (Spotify → Apple Music)

Base URL: `https://api.music.apple.com/v1`

| Purpose | Spotify (current) | Apple Music |
|---|---|---|
| Search a track | `GET /search?type=track&limit=10` | `GET /catalog/{storefront}/search?types=songs&limit=25&term=...` |
| Result cap | 10 | 25 (higher — nicer for matching) |
| Storefront | n/a | required (e.g. `us`); get via `GET /me/storefront` or hardcode |
| Create playlist | `POST /me/playlists` | `POST /me/library/playlists` |
| Add tracks | `POST /playlists/{id}/items` | `POST /me/library/playlists/{id}/tracks` |
| Replace all items | `PUT /playlists/{id}/items` | **⚠ not cleanly supported — see §6** |
| List own playlists | `GET /me/playlists` | `GET /me/library/playlists` |
| Track identity | Spotify URI (`spotify:track:...`) | **catalog song id** (numeric-ish string), `type: "songs"` |

**Create-playlist body shape (Apple):**
```json
{
  "attributes": { "name": "AI DJ — Chill", "description": "..." },
  "relationships": { "tracks": { "data": [ { "id": "<catalog song id>", "type": "songs" } ] } }
}
```
**Add-tracks body shape (Apple):** `{ "data": [ { "id": "<song id>", "type": "songs" } ] }`

Note the **catalog id vs. library id** split: you search the *catalog* (ids like `1440* ...`) but the
created playlist lives in the *library* with a `p.xxxxx` id. Matching reads catalog ids; find-by-name
for update mode reads library playlists.

---

## 6. ⚠ The #1 open question — update ("replace contents") mode

Our standing-playlist model relies on **update mode = replace the playlist's whole track list**
(Spotify `PUT /playlists/{id}/items`). **Apple Music's library-playlist API has historically been
append-only** — you can create and add tracks, but removing/reordering tracks in a *library* playlist
via the API has been limited or unsupported for long stretches. Apple has added some editing over time,
so **verify current capability at implementation time.** Fallbacks if replace-all still isn't supported:
- **Recreate:** delete + recreate the playlist each build (loses the stable share URL, but simple).
- **Append-only + de-dupe:** treat standing playlists as growing; skip tracks already present.
- **Full-replace via delete-then-add** if Apple exposes track removal by that point.

This is the single biggest semantic difference from the Spotify port and should be settled first.

---

## 7. GitHub Actions secrets (replaces `SPOTIFY_REFRESH_TOKEN`)

| Secret | What it is |
|---|---|
| `APPLE_PRIVATE_KEY` | Contents of the `.p8` MusicKit private key (multiline). **Never commit the `.p8`.** |
| `APPLE_KEY_ID` | The MusicKit key's Key ID. |
| `APPLE_TEAM_ID` | Apple Developer Team ID. |
| `APPLE_MUSIC_USER_TOKEN` | The Music User Token from the MusicKit-JS bootstrap (§3b/§4). |

The developer token is *derived* in-run from the first three — it is not itself a stored secret.

---

## 8. Code-change checklist (when we build it)

- [ ] `apple_auth.py` — sign the ES256 developer JWT from `APPLE_PRIVATE_KEY` + Key/Team IDs; expose
      `get_developer_token()` and read `APPLE_MUSIC_USER_TOKEN`. CI-guard like `spotify_auth.py` (fail
      fast if secrets are missing). Add `PyJWT[crypto]` to `requirements.txt`.
- [ ] `push_playlist_apple.py` (or a `--platform` flag on the resolver) — swap the base URL, search
      endpoint, and create/add endpoints per §5; keep `_score`/matching untouched; resolve to catalog
      song ids instead of URIs; implement update mode per whatever §6 resolves to.
- [ ] `.github/workflows/build-playlist.yml` — a parallel job (or matrix input) that runs the Apple
      resolver with the four Apple secrets. Could keep one workflow with a `platform` input.
- [ ] `tools/musickit-auth.html` — the one-time MUT bootstrap page.
- [ ] Keep specs shared: the same `specs/*.json` should build to either platform. The only per-platform
      state is the resolved id list, which is computed fresh each run — so nothing in the spec changes.

**Design principle:** curation engine (shared) vs. delivery target (per-platform). Don't fork the
taste profile or specs — only the delivery layer differs. This keeps "run to Spotify" and "run to
Apple Music" as two outputs of one brain, which also enables option 2 below.

---

## 9. Strategic options (unchanged from the chat that produced this)

1. **Stay on Spotify** — $0 beyond Duo. Current state.
2. **Add Apple Music alongside Spotify** — keep both delivery layers on the shared brain; compare
   curation quality directly. Costs $99 + Apple sub.
3. **Fully switch to Apple Music** — only if resubscribing to Apple Music regardless.

The architecture in §8 is deliberately option-2-friendly, so choosing later costs nothing now.

---

## 10. Why Apple's API is actually the *better* platform (the upside)

Despite the cost, Apple Music's API is stronger than what Spotify's shrinking dev mode leaves us:
- **Stable** — no track record of yanking endpoints mid-project (Spotify cut discovery in Nov 2024
  and more in Feb 2026; see the main handoff §3).
- **Search cap 25** vs. Spotify's 10 — better match candidates per query.
- Writes to your **real library playlists**, which is where Apple listening actually lives.

The trade is: *paid but solid* (Apple) vs. *free but eroding* (Spotify dev mode).
