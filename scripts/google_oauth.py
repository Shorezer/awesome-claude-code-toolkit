#!/usr/bin/env python3
"""Shared Google OAuth 2.0 (Desktop) helper.

The zandpai.com Workspace org blocks service-account key creation, so the
pipeline authenticates with an OAuth 2.0 Desktop client instead. One consent
covers both Sheets and YouTube; the resulting token is cached and refreshed.

Env vars:
  YOUTUBE_CLIENT_SECRET_PATH  path to the downloaded Desktop client_secret JSON
                              (default: credentials/client_secret.json)
  GOOGLE_SHEETS_CREDS_PATH    where the authorized-user token is cached
                              (default: credentials/google_oauth_token.json)
  YOUTUBE_CLIENT_ID           used to build a client config if the JSON file
  YOUTUBE_CLIENT_SECRET       is absent (fallback to env-only configuration)
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Union of scopes used across the pipeline. Requesting both up front means a
# single consent / token works for Sheets reads/writes and YouTube uploads.
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/youtube.upload",
]


def _client_secret_path():
    return os.environ.get("YOUTUBE_CLIENT_SECRET_PATH", "credentials/client_secret.json")


def _token_path():
    return os.environ.get("GOOGLE_SHEETS_CREDS_PATH", "credentials/google_oauth_token.json")


def _build_flow(scopes):
    """Prefer the downloaded client_secret JSON; fall back to env vars."""
    path = _client_secret_path()
    if os.path.exists(path):
        return InstalledAppFlow.from_client_secrets_file(path, scopes)

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if client_id and client_secret:
        config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        return InstalledAppFlow.from_client_config(config, scopes)

    raise FileNotFoundError(
        f"OAuth client secret not found at {path}, and YOUTUBE_CLIENT_ID / "
        "YOUTUBE_CLIENT_SECRET are not set. Download the Desktop OAuth client "
        "JSON from Google Cloud Console (project: concise-crane-495108-d3) and "
        f"save it to {path}."
    )


def load_credentials(scopes=None):
    """Return valid OAuth credentials, running the consent flow if needed.

    First call (no cached token) opens a browser for consent via a local
    redirect server, so it must run on a machine with a browser. After that,
    the cached token is reused and silently refreshed.
    """
    scopes = scopes or DEFAULT_SCOPES
    token_path = _token_path()

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = _build_flow(scopes).run_local_server(port=0)
        os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds


if __name__ == "__main__":
    # Run directly to perform the first-run consent and cache the token.
    load_credentials()
    print(f"Token saved to {_token_path()}")

