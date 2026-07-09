"""
print_refresh_token.py — shows your saved Spotify refresh token.

You run this ONCE, locally, to get the value you'll paste into GitHub as a
secret (so the cloud/Actions runs can act on your account without you being
at your Dell).

WHAT A REFRESH TOKEN IS (plain language): it's a long-lived key that lets the
app get fresh, short-lived access without logging in again. It is NOT your
Spotify password, and it only grants the permissions you already approved
(editing your playlists). Still — treat it like a password: don't paste it
anywhere public. GitHub secrets store it encrypted.

Run it with:  python print_refresh_token.py
"""

import json

from config import TOKEN_CACHE_FILE


def main():
    try:
        with open(TOKEN_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise SystemExit(
            "No saved login found. Run `python export_playlists.py` (or "
            "pipe_test.py) once first to log in, then try again."
        )

    token = data.get("refresh_token")
    if not token:
        raise SystemExit("No refresh token in the saved login — log in again first.")

    print("\n" + "-" * 60)
    print("Copy the line below and paste it as the GitHub secret")
    print("named  SPOTIFY_REFRESH_TOKEN :")
    print("-" * 60 + "\n")
    print(token)
    print("\n" + "-" * 60)
    print("Keep it private — anyone with it can edit your playlists.")
    print("-" * 60)


if __name__ == "__main__":
    main()
