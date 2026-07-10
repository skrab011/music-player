# handoff.md — planning brief for "the brother's version" of the AI DJ

**Purpose:** hand this to a fresh planning session (intended: a Claude Fable 5
session) to design a copy of this AI DJ project for Jacob's brother. Everything
needed to start planning is below; the repo root has the working reference
implementation.

**Read alongside:** `sharing-options.md` (in this folder) — the full menu of
options we talked through. This doc is the condensed, decision-oriented brief.

---

## What the project is (30 seconds)

A personal AI playlist curator. Claude generates a tracklist from a mood/taste
prompt; `push_playlist.py` (repo root) resolves each track against Spotify and
creates/updates a playlist on the user's account via GitHub Actions; the user
listens in the official Spotify app. The project never plays audio. Spotify's API
is used only for catalog search + playlist create/update — **all curation
intelligence comes from the model.**

Reference files at repo root: `README.md`, `CLAUDE.md` (working
guide + rules), `push_playlist.py` (the delivery engine), `spotify_auth.py` /
`get_token.py` / `config.py` (auth), `.github/workflows/build-playlist.yml`
(the runner), `specs/*.json` (example playlist specs), `taste-profile.md`
(Jacob's personal taste — **not** reusable for the brother).

---

## The goal for his version

His stated ask is just "the Spotify thing." The leading interpretation:
**on-demand curation he drives by chatting with a bot**, with **no AI
subscription** — powered by Jacob's Anthropic API key on a cheap model (Haiku).
(A secondary idea — an auto-refreshing "better algorithm" of standing playlists
on a schedule — is documented in `sharing-options.md` if he prefers that; confirm
with him before building either.)

---

## What's reusable vs. personal

**Reusable as-is (copy the code):**
- `push_playlist.py` — the whole resolve-and-build engine.
- `spotify_auth.py`, `get_token.py`, `config.py` — auth (PKCE + refresh-token).
- The spec JSON format (`specs/*.json`) — name/description/public/mode/tracks.
- `.github/workflows/build-playlist.yml` — the Actions runner.

**Personal (the brother needs his own — cannot inherit Jacob's):**
- His own **Spotify Developer app** → Client ID (not a secret) in `config.py`.
- His own **refresh token** (`get_token.py`, once, on a real computer) → GitHub
  secret `SPOTIFY_REFRESH_TOKEN` in his repo.
- His own **`taste-profile.md`** (reusing Jacob's would give him Jacob's taste).
- His own **GitHub repo** (fork/copy) so the Action + secret live under him.

**Constraints already settled:**
- Spotify Premium: **covered** — he's on Jacob's Duo plan.
- Setup labor: **Jacob will do it** (Spotify dev app, token, secret, repo) — the
  one-time PKCE token step needs a real computer + browser once.
- The taste profile is the one piece the brother must participate in.

---

## The chosen architecture (to detail in planning)

**Shared API key + messaging bot, on-demand, on Haiku.**

```
Brother texts a bot  →  bot backend (holds Jacob's API key)
                          │
                          ├─ calls Anthropic API (claude-haiku-4-5) with his
                          │  taste-profile.md → generates tracklist as JSON
                          │
                          ├─ triggers the playlist build (commit spec + auto-run
                          │  the Action, OR call the build directly)
                          │
                          └─ texts back the Spotify playlist link
```

**Why this shape:**
- The consumer Claude app can't take an API key (subscription auth only), so the
  bot is how he "chats to the API."
- Haiku is ~$1/M input, $5/M output → **~1–2¢ per playlist, ~$1–2/mo**. A metered
  API key beats a $20 sub for this unattended/low-volume use.
- Delivery (`push_playlist.py` + Actions) is already automated — the bot only
  needs to generate the spec and kick the build.

**Messaging surface options:**
- **Telegram** — easiest to build, free, no phone number, iOS-native. Recommended default.
- **SMS via Twilio** — literal "text a number," ~$1/mo number + pennies/text.

**Sharing Jacob's account safely (hard requirement):**
- **Dedicated API key in a spend-capped Anthropic Workspace** (e.g. $5/mo cap) so
  the DJ usage is walled off from Jacob's main account.
- **Key lives server-side** in the bot backend Jacob controls — the brother never
  sees it. Do NOT paste the raw key into an app on the brother's phone.

---

## Open design decisions for the planning session

1. **Messaging surface:** Telegram vs SMS/Twilio (vs iOS Shortcut as a fallback).
2. **Where the bot backend runs:** serverless function (Cloudflare Worker / Vercel
   / AWS Lambda) vs a tiny always-on process. Needs a public HTTPS endpoint for
   the webhook.
3. **How the bot triggers the build:** (a) commit the spec to his repo + add an
   `on: push: paths: specs/**` trigger to the workflow so it auto-builds; or
   (b) call the GitHub API to `workflow_dispatch`; or (c) port the resolve/build
   logic into the bot itself. (a) is likely cleanest.
4. **Conversation depth:** one-shot ("moody playlist") vs a short multi-turn
   refine loop. Multi-turn needs the bot to hold thread state.
5. **Prompt design:** how the taste profile is injected (prompt-cache it), and how
   the model returns a clean spec JSON (structured outputs / a strict schema).
6. **Anti-abuse / cost guard:** spend cap is the backstop; consider a simple
   allowlist so only the brother's number/chat can invoke it.
7. **Whether to also give him the auto-refreshing standing-playlist mode** (the
   secondary product in `sharing-options.md`) — confirm with the brother first.

---

## Suggested build phases (rough)

- **Phase 0 — replicate the pipe on his account:** Jacob sets up the Spotify dev
  app, runs `get_token.py`, stores the secret, copies the repo, and confirms a
  hand-made spec builds a playlist via the Action. (Same as Jacob's Phase 0.)
- **Phase 1 — taste profile:** build his `taste-profile.md` (export his playlists
  with `export_playlists.py` + a short interview).
- **Phase 2 — the bot:** message → Haiku → spec → build → reply link. Start with
  Telegram + one-shot curation.
- **Phase 3 — polish:** multi-turn refine, prompt-cache the profile, allowlist,
  spend-cap verification.

---

## Model / API notes for the planning session

- Curation is a text-generation + structured-output task — **`claude-haiku-4-5`**
  is the intended model (cheap, plenty capable for a tracklist). Confirm current
  pricing/model IDs via the `claude-api` skill when building.
- Use structured outputs / a strict JSON schema so the model returns a valid spec
  (`name`, `description`, `public`, `mode`, `tracks[]`) every time.
- Prompt-cache the taste profile (stable prefix) to cut per-call cost further.
- The cloud sandbox can't reach Spotify (egress) — all Spotify calls happen in
  Actions or on a real machine; the bot backend must reach both Anthropic and
  (to trigger builds) GitHub.
