"""
spotify_auth.py — logs you into Spotify and keeps you logged in.

============================ WHAT THIS DOES ============================

To touch your Spotify account, our scripts need an "access token" — a
temporary password Spotify hands out after you log in and approve. Access
tokens expire after about an hour, so Spotify also gives us a longer-lived
"refresh token" we can quietly trade in for a fresh access token, without
you logging in again.

We get that first pair using a flow called PKCE (pronounced "pixie"). PKCE
is the safe way for an app with NO secret of its own (like ours) to log a
user in:

  1. We invent a random secret string (the "code verifier") and keep it.
  2. We send Spotify a scrambled fingerprint of it (the "code challenge").
  3. You approve access in your browser; Spotify sends back a one-time code.
  4. We hand Spotify that code PLUS the original secret string. Because the
     secret matches the fingerprint it sent earlier, Spotify knows the code
     is really being redeemed by us, and hands over the tokens.

Nobody can hijack the login by intercepting that one-time code, because
they'd also need the secret string — and that never leaves this machine.

After the first login we cache the tokens in a local (gitignored) file and
just auto-refresh them from then on. The only function other scripts need
is get_access_token().

=======================================================================
"""

import base64
import hashlib
import http.server
import json
import os
import secrets
import time
import urllib.parse
import webbrowser

import requests

from config import CLIENT_ID, REDIRECT_PORT, REDIRECT_URI, SCOPES, TOKEN_CACHE_FILE

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"


# --------------------------------------------------------------------- #
# The one function other scripts call.
# --------------------------------------------------------------------- #

def get_access_token():
    """Return a currently-valid access token, doing whatever it takes to
    get one: use a cached token, refresh an expired one, or run the full
    browser login the first time."""

    # Path for GitHub Actions / any non-interactive run: if a refresh token
    # is supplied via the environment, just use it. No browser, no cache.
    env_refresh = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    if env_refresh:
        tokens = _refresh(env_refresh)
        return tokens["access_token"]

    tokens = _load_cached_tokens()

    if tokens is None:
        # First time on this machine — do the full browser login.
        tokens = _interactive_login()
        _save_tokens(tokens)
    elif time.time() >= tokens["expires_at"] - 60:
        # We have tokens but the access token is expired (or about to be).
        # Silently trade the refresh token for a fresh one.
        tokens = _refresh(tokens["refresh_token"], previous=tokens)
        _save_tokens(tokens)

    return tokens["access_token"]


# --------------------------------------------------------------------- #
# Token cache (a small JSON file on disk).
# --------------------------------------------------------------------- #

def _load_cached_tokens():
    if not os.path.exists(TOKEN_CACHE_FILE):
        return None
    with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_tokens(tokens):
    with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)


# --------------------------------------------------------------------- #
# PKCE helpers.
# --------------------------------------------------------------------- #

def _make_pkce_pair():
    """Return (code_verifier, code_challenge). The verifier is our secret;
    the challenge is its SHA-256 fingerprint, base64url-encoded."""
    verifier = secrets.token_urlsafe(64)  # ~86 URL-safe chars, well within spec
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


# --------------------------------------------------------------------- #
# The interactive browser login (only runs the very first time).
# --------------------------------------------------------------------- #

def _interactive_login():
    verifier, challenge = _make_pkce_pair()
    state = secrets.token_urlsafe(16)  # guards against a mismatched callback

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "scope": SCOPES,
        "state": state,
    }
    auth_url = AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)

    print("\nOpening your browser so you can log in to Spotify and approve access.")
    print("If it doesn't open automatically, paste this into your browser:\n")
    print("   " + auth_url + "\n")

    code = _catch_callback_code(state)
    webbrowser.open(auth_url)  # opened after the catcher is ready to listen

    # Trade the one-time code (+ our secret verifier) for real tokens.
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
    }
    resp = requests.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        raise SystemExit(
            "Login failed while exchanging the code for tokens.\n"
            f"  HTTP {resp.status_code}: {resp.text}"
        )
    return _tokens_from_response(resp.json())


def _catch_callback_code(expected_state):
    """Run a tiny web server on 127.0.0.1 that catches the single redirect
    Spotify makes back to us, and pull the one-time code out of it."""
    holder = {"code": None, "error": None}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if not parsed.path.startswith("/callback"):
                self.send_response(404)
                self.end_headers()
                return
            query = urllib.parse.parse_qs(parsed.query)
            if query.get("state", [None])[0] != expected_state:
                holder["error"] = "State mismatch — possible mixed-up login. Try again."
            elif "error" in query:
                holder["error"] = query["error"][0]
            else:
                holder["code"] = query.get("code", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Login complete — you can close this tab and return to the terminal."
            if holder["error"]:
                msg = "Login problem: " + holder["error"] + " — check the terminal."
            self.wfile.write(f"<html><body><h2>{msg}</h2></body></html>".encode("utf-8"))

        def log_message(self, *args):  # keep the terminal quiet
            pass

    server = http.server.HTTPServer(("127.0.0.1", REDIRECT_PORT), Handler)
    # Serve requests until we've captured a code or an error.
    while holder["code"] is None and holder["error"] is None:
        server.handle_request()
    server.server_close()

    if holder["error"]:
        raise SystemExit("Login failed: " + holder["error"])
    return holder["code"]


# --------------------------------------------------------------------- #
# Refreshing an expired access token.
# --------------------------------------------------------------------- #

def _refresh(refresh_token, previous=None):
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
    }
    resp = requests.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        raise SystemExit(
            "Could not refresh your Spotify login (the saved login may have "
            "been revoked). Delete the token cache file and run again to log "
            f"in fresh.\n  HTTP {resp.status_code}: {resp.text}"
        )
    body = resp.json()
    # Spotify doesn't always send a new refresh token on refresh; if it
    # doesn't, keep reusing the one we already have.
    if "refresh_token" not in body:
        body["refresh_token"] = refresh_token
    return _tokens_from_response(body)


def _tokens_from_response(body):
    return {
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
        "expires_at": time.time() + body.get("expires_in", 3600),
    }
