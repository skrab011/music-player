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

import json
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


def _extract_track(item):
    """Get the track object out of one API item.

    Playlist items and saved ("Liked") tracks wrap the track like
    {"track": {...}}. Top-tracks come back as the track object directly.
    Handle both shapes.
    """
    if not isinstance(item, dict):
        return item
    # Playlist items (Feb-2026 shape) wrap the track under "item"; the old
    # "track" key there is now just a boolean flag. Saved ("Liked") tracks
    # still wrap the track object under "track". Top-tracks are bare track
    # objects. Prefer whichever key actually holds a track object.
    if isinstance(item.get("item"), dict):
        return item["item"]
    if isinstance(item.get("track"), dict):
        return item["track"]
    return item


def _track_line(track):
    """Format one track as 'Artist1, Artist2 - Title', or None to skip it."""
    if not isinstance(track, dict):
        return None
    title = track.get("name")
    if not title:
        return None  # dropped/unavailable track, or a podcast episode
    artists = ", ".join(a.get("name", "") for a in track.get("artists", []) if a)
    return f"{artists} - {title}" if artists else title


def _lines_from(items):
    """Turn a page of API items into 'Artist - Title' lines, skipping junk.
    If items came back but none were usable, dump the first one so we can
    see its actual shape and fix the parser."""
    lines = [line for it in items if (line := _track_line(_extract_track(it)))]
    if items and not lines:
        print("     [debug] got items but couldn't read any track — first item was:")
        print("     " + json.dumps(items[0])[:600])
    return lines


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
        _write(_safe_filename(p["name"]), _lines_from(items))


def export_liked(token):
    print("Liked Songs:")
    items = _paginate(token, f"{API}/me/tracks", params={"limit": 50})
    _write("liked-songs.txt", _lines_from(items))


def export_top(token):
    print("Your all-time top tracks:")
    items = _paginate(
        token, f"{API}/me/top/tracks", params={"limit": 50, "time_range": "long_term"}
    )
    _write("top-tracks.txt", _lines_from(items))


def main():
    print("Exporting your Spotify library (read-only)...\n")
    os.makedirs(OUT_DIR, exist_ok=True)
    token = get_access_token()
    my_id = _my_id(token)

    # Run each section independently so one failure doesn't sink the rest.
    sections = (
        ("owned playlists", lambda: export_owned_playlists(token, my_id)),
        ("Liked Songs", lambda: export_liked(token)),
        ("top tracks", lambda: export_top(token)),
    )
    for label, fn in sections:
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
