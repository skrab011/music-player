"""
pipe_test.py — Phase 0 proof that the whole pipe works.

Run this once. It does, one time each, the four things the real AI DJ tool
will do over and over:

  1. Log in to Spotify (first run opens your browser; later runs are silent).
  2. Search the catalog for one known track.
  3. Create a playlist called "AI DJ — pipe test".
  4. Add that track to the playlist.

If all four print OK, open Spotify on your phone: the playlist should be
there with the track in it. That is the Phase 0 acceptance test.

Run it with:   python pipe_test.py

A few plain-language terms you'll see:
  - URI:  Spotify's permanent address for a track, like
          "spotify:track:2takcwOaAZWiXQijPHIx7B". Every track has one.
  - We talk to Spotify over the Web API — just web requests carrying our
    access token, which proves we're allowed to act on your account.
"""

import requests

from spotify_auth import get_access_token

API = "https://api.spotify.com/v1"

# The one track we'll prove the pipe with — thematically on-brand.
SEARCH_ARTIST = "Nujabes"
SEARCH_TITLE = "Aruarian Dance"

PLAYLIST_NAME = "AI DJ — pipe test"
PLAYLIST_DESCRIPTION = "Phase 0 pipe test. Safe to delete."


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _fail(what, resp):
    """Fail loud: say exactly what broke, and what Spotify said back."""
    raise SystemExit(
        f"\nFAILED at: {what}\n"
        f"  HTTP {resp.status_code}\n"
        f"  Spotify said: {resp.text}\n"
    )


def search_one_track(token):
    """Find a single track and return its URI + a readable name."""
    # Quoting the fields makes the match tighter than a loose keyword search.
    query = f'track:"{SEARCH_TITLE}" artist:"{SEARCH_ARTIST}"'
    resp = requests.get(
        f"{API}/search",
        headers=_auth_header(token),
        # limit max is 10 in dev mode now; we only need the top hit.
        params={"q": query, "type": "track", "limit": 1},
    )
    if resp.status_code != 200:
        _fail("searching for the track", resp)

    items = resp.json().get("tracks", {}).get("items", [])
    if not items:
        raise SystemExit(
            f"\nSearch returned no results for {SEARCH_ARTIST} - {SEARCH_TITLE}.\n"
            "That's unexpected for this track; something may be off with the query.\n"
        )

    track = items[0]
    artists = ", ".join(a["name"] for a in track["artists"])
    name = f"{artists} - {track['name']}"
    return track["uri"], name


def create_playlist(token):
    """Create a new empty playlist on your account and return its id."""
    # Note: POST /me/playlists (the old /users/{id}/playlists was removed).
    resp = requests.post(
        f"{API}/me/playlists",
        headers=_auth_header(token),
        json={
            "name": PLAYLIST_NAME,
            "public": True,          # per our decision: playlists are public
            "description": PLAYLIST_DESCRIPTION,
        },
    )
    if resp.status_code not in (200, 201):
        _fail("creating the playlist", resp)
    return resp.json()["id"]


def add_track(token, playlist_id, uri):
    """Add one track to the playlist.

    Spotify's Feb-2026 changes reportedly renamed this endpoint from
    /tracks to /items. We can't confirm the exact path without hitting it,
    so we try the new name first and fall back to the old one — and print
    which worked, so Phase 0 tells us the truth for the rest of the build.
    """
    body = {"uris": [uri]}
    last_resp = None
    for path in ("items", "tracks"):
        resp = requests.post(
            f"{API}/playlists/{playlist_id}/{path}",
            headers=_auth_header(token),
            json=body,
        )
        last_resp = resp
        if resp.status_code in (200, 201):
            return path  # the endpoint that actually worked
        if resp.status_code != 404:
            _fail(f"adding the track (via /{path})", resp)
    _fail("adding the track (both /items and /tracks returned 404)", last_resp)


def main():
    print("Phase 0 pipe test — proving auth -> search -> create -> add.\n")

    print("1/4  Logging in to Spotify...")
    token = get_access_token()
    print("     OK — logged in.\n")

    print(f"2/4  Searching for: {SEARCH_ARTIST} - {SEARCH_TITLE} ...")
    uri, found_name = search_one_track(token)
    print(f"     OK — found: {found_name}")
    print(f"     URI: {uri}\n")

    print(f'3/4  Creating playlist: "{PLAYLIST_NAME}" ...')
    playlist_id = create_playlist(token)
    print(f"     OK — created (id: {playlist_id})\n")

    print("4/4  Adding the track to the playlist...")
    used_path = add_track(token, playlist_id, uri)
    print(f"     OK — added (endpoint that worked: /{used_path})\n")

    print("=" * 60)
    print("SUCCESS. Open Spotify on your phone and look for the playlist")
    print(f'"{PLAYLIST_NAME}". It should contain: {found_name}')
    print("=" * 60)


if __name__ == "__main__":
    main()
