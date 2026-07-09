"""
get_token.py — one-file Spotify login that prints your refresh token.

PURPOSE: get the value for the GitHub secret SPOTIFY_REFRESH_TOKEN from ANY
computer with Python + a browser — your Dell, or a work PC. It uses only the
Python standard library (no `pip install` needed) and does NOT save anything
to disk, so it leaves no trace on a shared/work machine.

RUN:  python get_token.py

It opens your browser, you log in and click Agree, and it prints one long line
— your refresh token — to paste into the GitHub secret box.
"""

import base64
import hashlib
import http.server
import json
import secrets
import urllib.parse
import urllib.request
import webbrowser

CLIENT_ID = "1be6c7e3f0844be9911c1fd3d4745142"
PORT = 8888
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"
SCOPES = ("playlist-modify-public playlist-modify-private playlist-read-private "
          "playlist-read-collaborative user-library-read user-top-read")
AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"


def main():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    state = secrets.token_urlsafe(16)

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

    print("\nOpening your browser to log in to Spotify. If it doesn't open,")
    print("paste this into your browser:\n")
    print("   " + auth_url + "\n")

    holder = {"code": None, "error": None}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if not parsed.path.startswith("/callback"):
                self.send_response(404)
                self.end_headers()
                return
            q = urllib.parse.parse_qs(parsed.query)
            if q.get("state", [None])[0] != state:
                holder["error"] = "state mismatch"
            elif "error" in q:
                holder["error"] = q["error"][0]
            else:
                holder["code"] = q.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Done. Close this tab and return "
                             b"to the terminal.</h2></body></html>")

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    webbrowser.open(auth_url)
    while holder["code"] is None and holder["error"] is None:
        server.handle_request()
    server.server_close()

    if holder["error"]:
        raise SystemExit("Login failed: " + holder["error"])

    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": holder["code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
    }).encode()

    try:
        with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=data)) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Token exchange failed: HTTP {e.code}\n  {e.read().decode()}")

    token = body.get("refresh_token", "")
    print("\n" + "-" * 60)
    print("Paste the line below as the GitHub secret SPOTIFY_REFRESH_TOKEN:")
    print("-" * 60 + "\n")
    print(token)
    print("\n" + "-" * 60)
    print("Keep it private. Nothing was saved to this computer.")
    print("-" * 60)


if __name__ == "__main__":
    main()
