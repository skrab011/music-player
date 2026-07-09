"""
check_login.py — confirms your saved Spotify login still works.

This has NO side effects: it doesn't create, change, or delete anything.
It just asks spotify_auth for a valid access token and reports back.

Why it exists: the Phase 0 acceptance test has two halves. The first
(the full round-trip) is proven by pipe_test.py. The second is durability
— that a day later your login still works WITHOUT you re-approving in a
browser. Once the access token from your first login has expired (about an
hour, so "tomorrow" is a safe bet), run this. If it prints OK and never
opens a browser, your auto-refresh works and Phase 0 is fully closed.

Run it with:  python check_login.py
"""

from spotify_auth import get_access_token


def main():
    print("Checking your saved Spotify login (no browser should open)...")
    token = get_access_token()
    if token:
        print("OK — your login is valid and was refreshed silently. No re-login needed.")
    else:
        print("Problem — no token came back. Tell Claude what you see above.")


if __name__ == "__main__":
    main()
