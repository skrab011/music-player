"""
export_playlists.py — dumps your Spotify library to plain text.

This is READ-ONLY. It creates, changes, and deletes nothing on your
account. It just reads and writes text files into a local seed-playlists/
folder, which becomes the raw material Claude uses to draft your taste
profile (Phase 1).

What it exports, each into its own .txt file (one "Artist - Title" per line):
  - every playlist you own
  - your Liked Songs
  - your all-time top tracks (Spotify's view of what you play most)

If any one section isn't available (Spotify keeps changing what's allowed),
it prints a note and keeps going — a partial export is still useful.

Run it with:  python export_playlists.py

Then commit and push the seed-playlists/ folder so Claude can read it:
  git add seed-playlists
  git commit -m "Add exported playlists as taste seed data"
  git push
"""

import os
import re

import requests

from spotify_auth import get_access_token

API = "https://api.spotify.com/v1"
OUT_DIR = "seed-playlists"


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _safe_filename(name):
    """Turn a playlist name into a tidy filename, e.g. '80s Rock' -> '80s-rock'."""
    cleaned = re.sub(r"[^\w\- ]", "", name).strip().lower()
    cleaned = re.sub(r"\s+", "-", cleaned)
    return (cleaned or "untitled") + ".txt"


def _track_line(track):
    """Format one track as 'Artist1, Artist2 - Title', or None to skip it."""
    if not track or track.get("type") != "track":
        return None  # skip podcast episodes, unavailable/local tracks, etc.
    artists = ", ".join(a["name"] for a in track.get("artists", []))
    title = track.get("name", "")
    if not title:
        return None
    return f"{artists} - {title}"


def _paginate(token, url, params=None):
    """Follow Spotify's paging ('next' links) and return all items across
    pages. Raises with a clear message if a request fails."""
    items = []
    while url:
        resp = requests.get(url, headers=_auth(token), params=params)
        params = None  # only the first page uses our params; 'next' has them baked in
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code} from {url}\n  {resp.text}")
        data = resp.json()
        items.extend(data.get("items", []))
        url = data.get("next")
    return items


def _write(filename, lines):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"     wrote {len(lines):>4} tracks -> {path}")


def _my_id(token):
    resp = requests.get(f"{API}/me", headers=_auth(token))
    if resp.status_code != 200:
        raise RuntimeError(f"Couldn't read your profile: HTTP {resp.status_code}\n  {resp.text}")
    return resp.json()["id"]


def export_owned_playlists(token, my_id):
    print("Playlists you own:")
    playlists = _paginate(token, f"{API}/me/playlists", params={"limit": 50})
    mine = [p for p in playlists if p.get("owner", {}).get("id") == my_id]
    if not mine:
        print("     (none found that you own)")
    for p in mine:
        # Read this playlist's tracks. The endpoint is /items (Feb-2026 rename).
        items = _paginate(token, f"{API}/playlists/{p['id']}/items", params={"limit": 50})
        lines = [line for it in items if (line := _track_line(it.get("track")))]
        _write(_safe_filename(p["name"]), lines)


def export_liked(token):
    print("Liked Songs:")
    items = _paginate(token, f"{API}/me/tracks", params={"limit": 50})
    lines = [line for it in items if (line := _track_line(it.get("track")))]
    _write("liked-songs.txt", lines)


def export_top(token):
    print("Your all-time top tracks:")
    # Top items come back as track objects directly (no 'track' wrapper).
    items = _paginate(
        token, f"{API}/me/top/tracks", params={"limit": 50, "time_range": "long_term"}
    )
    lines = [line for t in items if (line := _track_line(t))]
    _write("top-tracks.txt", lines)


def main():
    print("Exporting your Spotify library (read-only)...\n")
    os.makedirs(OUT_DIR, exist_ok=True)
    token = get_access_token()
    my_id = _my_id(token)

    # Run each section independently so one failure doesn't sink the rest.
    for label, fn in (
        ("owned playlists", lambda: export_owned_playlists(token, my_id)),
        ("Liked Songs", export_liked),
        ("top tracks", export_top),
    ):
        try:
            fn()
        except Exception as e:
            print(f"     SKIPPED {label} — {e}\n")
        else:
            print()

    print("=" * 60)
    print(f"Done. Check the '{OUT_DIR}' folder, then push it up:")
    print("   git add seed-playlists")
    print('   git commit -m "Add exported playlists as taste seed data"')
    print("   git push")
    print("=" * 60)


if __name__ == "__main__":
    main()
