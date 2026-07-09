"""
push_playlist.py — turn a tracklist into a real playlist on your account.

This is the engine. Claude generates a "spec" (a small JSON file naming the
playlist and listing the songs); this script resolves each song to a real
Spotify track and builds (or updates) the playlist.

WHAT IT DOES, step by step:
  1. Reads the spec file you point it at.
  2. For every song, searches Spotify and picks the BEST match — preferring
     the normal studio version over live/remix/karaoke/cover versions.
  3. Sorts each song into: MATCH (confident), WEAK (found something, but I'm
     not sure), or MISS (couldn't find it).
  4. Creates a new playlist, or replaces the contents of an existing one.
  5. Prints a report. MATCH + WEAK go into the playlist; WEAK and MISS are
     listed so Claude can double-check and substitute. (You don't have to.)

RUN IT:
    python push_playlist.py <spec.json>

SPEC FORMAT (JSON):
    {
      "name": "AI DJ — Chill",
      "description": "Low-key, winding down.",
      "public": true,
      "mode": "create",              # "create" or "update"
      "tracks": [
        "Alec Benjamin - Let Me Down Slowly",
        {"artist": "Death Cab for Cutie", "title": "I Will Follow You into the Dark"}
      ]
    }
Tracks can be "Artist - Title" strings or {artist, title} objects.

A "URI" below is Spotify's permanent address for a track, e.g.
"spotify:track:4sUTagdmyuyAxd7RvbygpQ" — that's what playlists actually store.
"""

import difflib
import json
import re
import sys
import time

import requests

from spotify_auth import get_access_token

API = "https://api.spotify.com/v1"

# Candidate-title keywords that usually mean "not the version we want,"
# unless the request itself asked for them.
BAD_VERSION_WORDS = [
    "live", "karaoke", "cover", "tribute", "made famous", "remix",
    "sped up", "slowed", "8d", "instrumental", "reverb", "loop",
]

# Confidence thresholds for the match score (0..1).
MATCH_THRESHOLD = 0.82
WEAK_THRESHOLD = 0.60


# --------------------------------------------------------------------- #
# Small text helpers for fuzzy matching.
# --------------------------------------------------------------------- #

def _norm(s):
    """Lowercase, drop punctuation, collapse spaces — so 'P!nk' ~ 'pink'."""
    s = s.lower()
    s = re.sub(r"\(feat[^)]*\)", " ", s)      # drop "(feat. X)"
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def _ratio(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def _artist_score(query_artist, candidate_artists):
    qa = _norm(query_artist)
    best = 0.0
    for a in candidate_artists:
        na = _norm(a)
        if qa == na or (qa and (qa in na or na in qa)):
            return 1.0
        best = max(best, _ratio(qa, na))
    return best


def _title_score(query_title, candidate_title):
    qt, ct = _norm(query_title), _norm(candidate_title)
    if qt == ct:
        return 1.0
    if qt and (qt in ct or ct in qt):
        return 0.9
    return _ratio(qt, ct)


def _version_penalty(query_title, candidate_title):
    """Penalize live/remix/karaoke/etc. — but only if the request didn't ask."""
    q, c = query_title.lower(), candidate_title.lower()
    for word in BAD_VERSION_WORDS:
        if word in c and word not in q:
            return 0.25
    return 0.0


def _score(query_artist, query_title, item):
    cand_artists = [a["name"] for a in item.get("artists", [])]
    a = _artist_score(query_artist, cand_artists)
    t = _title_score(query_title, item.get("name", ""))
    pen = _version_penalty(query_title, item.get("name", ""))
    return max(0.0, 0.55 * t + 0.45 * a - pen)


# --------------------------------------------------------------------- #
# Spotify calls.
# --------------------------------------------------------------------- #

def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _search(token, query):
    # limit max is 10 in dev mode; the best match is almost always near the top.
    resp = requests.get(
        f"{API}/search",
        headers=_auth(token),
        params={"q": query, "type": "track", "limit": 10},
    )
    if resp.status_code != 200:
        raise SystemExit(f"\nSearch failed: HTTP {resp.status_code}\n  {resp.text}\n")
    return resp.json().get("tracks", {}).get("items", [])


def resolve_track(token, artist, title):
    """Return (status, uri, matched_label). status is 'match'/'weak'/'miss'."""
    # First a tight field-scoped search, then a looser fallback if needed.
    items = _search(token, f'track:"{title}" artist:"{artist}"')
    if not items:
        items = _search(token, f"{artist} {title}")
    time.sleep(0.1)  # be polite to the rate limiter

    best, best_score = None, 0.0
    for it in items:
        s = _score(artist, title, it)
        if s > best_score:
            best, best_score = it, s

    if best is None:
        return "miss", None, None

    label = f"{', '.join(a['name'] for a in best['artists'])} - {best['name']}"
    if best_score >= MATCH_THRESHOLD:
        return "match", best["uri"], label
    if best_score >= WEAK_THRESHOLD:
        return "weak", best["uri"], label
    return "miss", None, None


def _me_id(token):
    resp = requests.get(f"{API}/me", headers=_auth(token))
    if resp.status_code != 200:
        raise SystemExit(f"Couldn't read your profile: HTTP {resp.status_code}\n  {resp.text}")
    return resp.json()["id"]


def _find_playlist_by_name(token, name):
    """Return the id of a playlist you own with this exact name, or None."""
    url = f"{API}/me/playlists"
    params = {"limit": 50}
    me = _me_id(token)
    while url:
        resp = requests.get(url, headers=_auth(token), params=params)
        params = None
        if resp.status_code != 200:
            raise SystemExit(f"Couldn't list playlists: HTTP {resp.status_code}\n  {resp.text}")
        data = resp.json()
        for p in data.get("items", []):
            if p.get("owner", {}).get("id") == me and p.get("name") == name:
                return p["id"]
        url = data.get("next")
    return None


def _create_playlist(token, name, public, description):
    resp = requests.post(
        f"{API}/me/playlists",
        headers=_auth(token),
        json={"name": name, "public": public, "description": description},
    )
    if resp.status_code not in (200, 201):
        raise SystemExit(f"Couldn't create playlist: HTTP {resp.status_code}\n  {resp.text}")
    return resp.json()["id"]


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _add_items(token, pid, uris):
    """Append tracks (used after creating a fresh playlist), 100 at a time."""
    for chunk in _chunks(uris, 100):
        resp = requests.post(
            f"{API}/playlists/{pid}/items",
            headers=_auth(token),
            json={"uris": chunk},
        )
        if resp.status_code not in (200, 201):
            raise SystemExit(f"Couldn't add tracks: HTTP {resp.status_code}\n  {resp.text}")


def _replace_items(token, pid, uris):
    """Replace ALL of a playlist's tracks with these (used for update mode)."""
    # PUT replaces; if there are more than 100, PUT the first 100 then append.
    first = uris[:100]
    resp = requests.put(
        f"{API}/playlists/{pid}/items",
        headers=_auth(token),
        json={"uris": first},
    )
    if resp.status_code not in (200, 201):
        raise SystemExit(f"Couldn't replace tracks: HTTP {resp.status_code}\n  {resp.text}")
    if len(uris) > 100:
        _add_items(token, pid, uris[100:])


# --------------------------------------------------------------------- #
# Spec parsing.
# --------------------------------------------------------------------- #

def _parse_tracks(raw_tracks):
    """Accept 'Artist - Title' strings or {artist, title} objects."""
    parsed = []
    for t in raw_tracks:
        if isinstance(t, dict):
            artist, title = t.get("artist", ""), t.get("title", "")
        else:
            artist, _, title = str(t).partition(" - ")
        artist, title = artist.strip(), title.strip()
        if artist and title:
            parsed.append((artist, title))
        else:
            print(f"  ! skipping unparseable track entry: {t!r}")
    return parsed


# --------------------------------------------------------------------- #
# Main.
# --------------------------------------------------------------------- #

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python push_playlist.py <spec.json>")

    with open(sys.argv[1], encoding="utf-8") as f:
        spec = json.load(f)

    name = spec["name"]
    description = spec.get("description", "")
    public = spec.get("public", True)
    mode = spec.get("mode", "create")
    tracks = _parse_tracks(spec.get("tracks", []))

    if not tracks:
        raise SystemExit("No usable tracks in the spec.")

    print(f'Building "{name}"  ({mode} mode, {len(tracks)} tracks requested)\n')
    token = get_access_token()

    uris, weak, misses = [], [], []
    seen = set()
    for i, (artist, title) in enumerate(tracks, 1):
        status, uri, label = resolve_track(token, artist, title)
        want = f"{artist} - {title}"
        if status == "miss":
            misses.append(want)
            print(f"  {i:>2}. ✗ MISS   {want}")
        else:
            if uri not in seen:      # avoid duplicate tracks
                seen.add(uri)
                uris.append(uri)
            if status == "weak":
                weak.append(f"{want}   ->   {label}")
                print(f"  {i:>2}. ⚠ weak   {want}   ->   {label}")
            else:
                print(f"  {i:>2}. ✓ match  {label}")

    # Build the playlist.
    print()
    if mode == "update":
        pid = _find_playlist_by_name(token, name)
        if pid is None:
            print(f'No existing playlist named "{name}" — creating it instead.')
            pid = _create_playlist(token, name, public, description)
            _add_items(token, pid, uris)
        else:
            _replace_items(token, pid, uris)
            print(f'Replaced contents of existing "{name}".')
    else:
        pid = _create_playlist(token, name, public, description)
        _add_items(token, pid, uris)

    # Report.
    print("\n" + "=" * 64)
    print(f'"{name}" — {len(uris)} tracks added '
          f"({len(uris) - len(weak)} confident, {len(weak)} weak), {len(misses)} missed.")
    if weak:
        print("\nWEAK matches (Claude should eyeball these):")
        for w in weak:
            print(f"  ⚠ {w}")
    if misses:
        print("\nMISSED (Claude should substitute and re-run):")
        for m in misses:
            print(f"  ✗ {m}")
    print("=" * 64)
    print("Open Spotify and check the playlist.")


if __name__ == "__main__":
    main()
