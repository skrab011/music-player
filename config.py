"""
config.py — the handful of settings the AI DJ scripts need.

Plain-language note: nothing in here is a password. With the PKCE login
flow we use, there is NO client secret to protect, so the Client ID below
is safe to keep in the repo. The only sensitive thing (your logged-in
tokens) lives in a separate file that is gitignored — see TOKEN_CACHE_FILE.
"""

import os

# --- Your Spotify app ---------------------------------------------------

# The Client ID from your Spotify app's Settings page. Not a secret.
# Can be overridden with an environment variable (handy later for GitHub
# Actions), but the default is fine for running on your Dell.
CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "1be6c7e3f0844be9911c1fd3d4745142")

# --- Where Spotify sends your browser back after you approve access -----

# This MUST match, character for character, the Redirect URI you registered
# in the Spotify app settings. We use the loopback IP 127.0.0.1 (Spotify no
# longer accepts the literal word "localhost"). 8888 is just a port on your
# own machine that our script briefly listens on to catch the redirect.
REDIRECT_PORT = int(os.environ.get("SPOTIFY_REDIRECT_PORT", "8888"))
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"

# --- Local login cache --------------------------------------------------

# After you log in once, we save the tokens here so you don't have to log in
# again every time. This file is tied to YOUR account, so it is gitignored
# and must never be committed.
TOKEN_CACHE_FILE = os.environ.get("SPOTIFY_TOKEN_CACHE", ".spotify_token.json")

# --- Permissions we ask Spotify for -------------------------------------

# The access our scripts need. "modify" = create/edit playlists (the DJ
# loop); "read" = see your existing playlists, Liked Songs, and top tracks
# (so we can learn your taste in Phase 1). If this list grows, the login
# code notices your saved login doesn't cover the new items and re-prompts
# you automatically.
SCOPES = " ".join([
    "playlist-modify-public",
    "playlist-modify-private",
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-library-read",
    "user-top-read",
])
