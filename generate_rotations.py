"""
generate_rotations.py — refresh the 7 standing playlists with fresh picks weekly.

WHAT THIS IS (plain language):
  Your 7 "AI DJ —" playlists are normally static — they only change when you ask.
  This script makes them rotate on their own. Once a week (via GitHub Actions) it
  asks Claude for a *new* batch of songs for each lane, leaning toward "adjacent
  deep cuts" — tracks clearly in your taste that you probably haven't heard yet.
  It then hands those tracklists to push_playlist.py, which rebuilds each playlist
  in place. The winners you love, you'll Like — and Liked Songs is your keeper.

HOW IT AVOIDS REPEATING ITSELF:
  It remembers the last several weeks of picks per lane (in rotation-history/)
  and tells Claude "don't use any of these again." So the discovery keeps moving.

WHAT IT NEEDS:
  - ANTHROPIC_API_KEY in the environment (your Anthropic API key). In GitHub
    Actions this comes from the repo secret of the same name.
  - taste-profile.md and the 7 spec files in specs/ (already in the repo).

RUN IT:
  python generate_rotations.py
  (It only writes the spec + history files. The workflow then runs push_playlist.py
   for each spec to actually build the playlists on Spotify.)
"""

import datetime
import json
import os
import pathlib

import anthropic

# --------------------------------------------------------------------- #
# Settings.
# --------------------------------------------------------------------- #

# Which model curates. Opus gives the deepest music knowledge; it's ~$1-2/month
# at this weekly volume. Set ANTHROPIC_MODEL=claude-haiku-4-5 to make it nearly
# free (a few cents/month) if you'd rather trade some depth for cost.
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")

# How many past weeks of picks to remember per lane (so they aren't repeated).
HISTORY_WEEKS = 8

# How many tracks to ask for per lane. A few extra covers the handful that
# push_playlist.py can't find on Spotify (those get dropped, not filled).
TRACKS_PER_LANE = 24

HISTORY_DIR = pathlib.Path("rotation-history")
PROFILE_FILE = pathlib.Path("taste-profile.md")

# The 7 standing playlists: which spec file, plus a one-line curation brief.
# Name / description / public are read from the existing spec — only the
# tracklist is regenerated — so these stay consistent with what you approved.
LANES = [
    {"spec": "specs/chill.json",
     "brief": "introspective singer-songwriter and moody indie; low-key, winding down"},
    {"spec": "specs/hype.json",
     "brief": "anthemic alt-pop-rock with big sing-along choruses; hype and catharsis"},
    {"spec": "specs/heavier.json",
     "brief": "melodic metalcore and harder melodic rock; tuneful-aggressive, screamed moments OK"},
    {"spec": "specs/summer.json",
     "brief": "bright, breezy, psych-tinged indie-pop with a summer feel"},
    {"spec": "specs/workout.json",
     "brief": "high-BPM, driving songs for running and workouts"},
    {"spec": "specs/country.json",
     "brief": "broad modern country; a go-to for driving"},
    {"spec": "specs/focus.json",
     "brief": "wordless or soft lo-fi, trip hop, and downtempo for focus; soft atmospheric vocals OK, no drama"},
]

# Hard taste guardrails (from taste-profile.md's Do-Not-Play list).
GUARDRAILS = """Hard rules — never violate:
- No pure screamo or relentless-breakdown metal. Ceiling: Of Mice & Men is TOO
  far. Melodic metalcore with screamed *moments* is fine; constant-screaming or
  no-chorus is out.
- No hard / technical / horrorcore rap (Hopsin, Tech N9ne, and similar).
- No Christian / worship music (except Christmas music in December).
- No classical."""

# Structured-output schema: Claude must return exactly this shape.
SCHEMA = {
    "type": "object",
    "properties": {
        "tracks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "artist": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["artist", "title"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tracks"],
    "additionalProperties": False,
}


# --------------------------------------------------------------------- #
# History (what we've already played) — stored per lane in rotation-history/.
# --------------------------------------------------------------------- #

def _history_file(lane_key):
    return HISTORY_DIR / f"{lane_key}.json"


def load_recent(lane_key):
    """Return a flat list of 'Artist - Title' strings from recent weeks."""
    f = _history_file(lane_key)
    if not f.exists():
        return []
    weeks = json.loads(f.read_text(encoding="utf-8"))
    recent = []
    for entry in weeks[-HISTORY_WEEKS:]:
        recent.extend(entry.get("tracks", []))
    return recent


def append_history(lane_key, tracks):
    """Record this week's picks, keeping only the last HISTORY_WEEKS weeks."""
    f = _history_file(lane_key)
    weeks = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    weeks.append({"week": datetime.date.today().isoformat(), "tracks": tracks})
    weeks = weeks[-HISTORY_WEEKS:]
    f.write_text(json.dumps(weeks, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------- #
# The curation call.
# --------------------------------------------------------------------- #

def build_system(profile):
    return (
        "You are Jacob's personal music curator for a weekly, auto-rotating set "
        "of playlists. Below is his taste profile — treat it as the source of "
        "truth for what fits him.\n\n"
        f"{profile}\n\n"
        f"{GUARDRAILS}\n\n"
        "Your job each week is DISCOVERY via 'adjacent deep cuts': songs that sit "
        "clearly inside the requested lane and his taste, but that he most likely "
        "has NOT heard. Favor lesser-known tracks, deeper album cuts, and newer or "
        "under-the-radar artists over obvious hits and radio staples — while "
        "staying recognizably in-lane. Never invent songs; only use real, "
        "released tracks you are confident exist."
    )


def generate_lane(client, system, brief, recent):
    recent_block = "\n".join(f"- {t}" for t in recent) if recent else "(none yet)"
    user = (
        f'Curate this week\'s playlist for the "{brief}" lane.\n'
        f"Give exactly {TRACKS_PER_LANE} tracks.\n"
        "Lean into adjacent deep cuts (see the system instructions).\n\n"
        "Do NOT reuse any of these recently-played tracks:\n"
        f"{recent_block}\n\n"
        "Return each track as an artist and a title."
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)["tracks"]


# --------------------------------------------------------------------- #
# Main.
# --------------------------------------------------------------------- #

def main():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    profile = PROFILE_FILE.read_text(encoding="utf-8")
    system = build_system(profile)
    HISTORY_DIR.mkdir(exist_ok=True)

    print(f"Rotating {len(LANES)} standing playlists with {MODEL}\n")
    for lane in LANES:
        spec_path = pathlib.Path(lane["spec"])
        lane_key = spec_path.stem
        spec = json.loads(spec_path.read_text(encoding="utf-8"))

        recent = load_recent(lane_key)
        tracks = generate_lane(client, system, lane["brief"], recent)

        # Keep name/description/public; force update mode; swap in the new tracks.
        spec["mode"] = "update"
        spec["tracks"] = [f'{t["artist"]} - {t["title"]}' for t in tracks]
        spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

        append_history(lane_key, spec["tracks"])
        print(f"  {lane_key:<8} -> {len(spec['tracks'])} fresh tracks "
              f"(avoided {len(recent)} recent)")

    print("\nDone. push_playlist.py will now build each refreshed spec.")


if __name__ == "__main__":
    main()
