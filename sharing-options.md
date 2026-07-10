# sharing-options.md — giving the AI DJ to someone else (WIP)

**What this is:** a scratch doc capturing the options we've talked through for
sharing this project with Jacob's brother. Nothing here is decided or built —
it's a living menu to iterate on. Brother's stated ask so far is just "the
Spotify thing" (he wants a copy); the real requirements are still TBD until
Jacob talks to him.

_Status: brainstorm. Last updated in-session. Add options freely._

---

## Context / constraints we've established

- **Spotify Premium: covered.** Brother is on Jacob's Duo plan, so the Premium
  requirement (noted in `spotify-ai-dj-CLAUDE.md`) is already satisfied.
- **Setup labor: Jacob will do it.** Jacob can handle the full technical setup
  on the brother's accounts — *except* the taste profile, which is personal.
- **Brother doesn't pay for AI.** No Claude/ChatGPT subscription today. Wants to
  *interact with a bot* to curate, not do a manual copy-paste workflow.
- **Key architecture fact (unchanged):** the project has two halves —
  **curation** (invent a tracklist) and **delivery** (`push_playlist.py` + the
  Build Playlist Action resolves it and builds the playlist). Delivery is
  already automated. Every option below only changes the *curation* half.

---

## Part 1 — What's portable vs. personal

The **code** is fully portable; the **data** is per-person and can't be
inherited from Jacob:

| Portable (copy as-is) | Personal (brother needs his own) |
|---|---|
| All `.py` scripts, the workflow, the spec format | His own **Spotify Developer app** → Client ID (not a secret) |
| The repo structure | His own **refresh token** (`get_token.py`, once, on a real computer) → GitHub secret `SPOTIFY_REFRESH_TOKEN` |
| | His own **`taste-profile.md`** (reusing Jacob's would just give him Jacob's taste) |
| | His own **GitHub repo** (fork/copy) so the Action + secret live under him |

One-time setup needs a real computer + browser once (the PKCE token step can't
be done on a phone/cloud). ~30 min with Jacob; after that, never again.

---

## Part 2 — The AI/bot question

The $20 Claude sub is **not** the load-bearing part. It buys *agentic
automation* (Claude writes the spec, triggers the Action, reads the logs — one
loop). The curation itself is just text generation any bot can do.

- **Free chatbot, decoupled:** any free tier (Claude/ChatGPT/Gemini) writes the
  tracklist JSON; brother pastes it into a spec via GitHub's web editor and runs
  the workflow. $0 AI. Tradeoff: manual, two apps.
- **Agentic Git bots (low/free tier):** GitHub Copilot (free tier, native GitHub
  integration, mobile) or Google Jules (free tier, GitHub integration). **Wrinkle:**
  these work by opening *pull requests*, not by triggering workflows — so
  something still has to run the build. Fix: auto-trigger the workflow on spec
  changes (`on: push: paths: specs/**`) so a PR-merge builds the playlist itself.
- **Paid agent (Claude Code / Codex):** ~$20/mo — no cheaper than Jacob's setup.

---

## Part 3 — Gotchas / what's easy to miss

- Premium required → **covered by Duo.**
- The refresh token is a real secret → GitHub Actions secret only, never committed.
- Re-auth needed if he changes his Spotify password or revokes access.
- This is a developer project, not an app — friction is all in the one-time
  setup, not the daily use.
- Spotify dev app stays in Development Mode (fine for one user).

---

## The curation models (the big fork)

Two different *products* are on the table. They share the delivery engine; they
differ in where the fresh tracklist comes from.

### On-demand (what Jacob has)
Human + chatbot generate a tracklist when asked. Interactive, steerable.
Best served by an agentic bot (or the free-chatbot-decoupled flow above).

### "Improved algorithm" — auto-refreshing standing playlists
Brother's alternative idea: N standing playlists that regenerate on a schedule
and overwrite in place (e.g. 15 weekly, or 5 daily). Delivery side is just a
`cron` on the workflow. Curation side has three flavors:

**Model A — No AI (pool sampler)**
- Each genre is a big static pool (~100 songs); script randomly picks ~25 per run.
- **Cost:** $0 forever. **Gives:** variety. **Missing:** discovery — only ever
  plays songs already in the pool, so not really "better than Spotify."

**Model B — Scheduled API generation (the real self-refreshing DJ)**
- Cron job feeds `taste-profile.md` to an LLM **API** (not an interactive
  session), which generates the tracklists; `push_playlist.py` builds them.
- **Cost:** this is the one case where dropping the $20 sub is the *smart* move —
  ~15 playlists/week is a few thousand tokens/run → realistically **cents–$1/mo**
  on metered API. No subscription; just a few dollars of API credit.
- **Not easier to build** than the interactive model (adds an unattended API key,
  a generator script, cron, prompt-tuning) — but genuinely cheaper.
- **Two wrinkles:**
  1. *Daily vs weekly is a UX call:* daily overwrite kills "keepers" (a banger
     found Tuesday is gone Wednesday). Weekly-15 = "15 flavors of Discover
     Weekly." Lean weekly unless he wants the churn.
  2. *Unattended AI repeats itself* unless you persist the last few weeks of
     tracklists and feed them back ("don't repeat these"). Also: LLM knowledge
     has a cutoff, so it's strong on deep cuts, weaker on brand-new releases.

**Reuse:** the "improved algorithm" reuses ~70% of what exists — delivery is
identical; only the curation front-end changes.

---

## Open decisions / next steps

- [ ] Talk to brother — on-demand vs. auto-refreshing? How much discovery matters?
- [ ] If auto-refreshing: cadence + count (weekly-15? daily-5?), and A vs B.
- [ ] If B: sort out anti-repetition memory + where the API key lives.
- [ ] Decide whether to add the auto-build-on-spec-change trigger (his repo, and
      whether Jacob's too).
- [ ] (Placeholder) Jacob's additional option based on the API-cost insight — TBD.
