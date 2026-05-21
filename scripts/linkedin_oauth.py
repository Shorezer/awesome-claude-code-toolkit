#!/usr/bin/env python3
"""LinkedIn OAuth 2.0 (authorization code) helper.

Mirrors the Google OAuth helper: runs a one-time browser consent against a
local callback server, exchanges the code for an access token, caches it, and
returns it on later calls.

LinkedIn member tokens are long-lived (~60 days) but usually have no refresh
token, so on expiry you re-run the consent flow.

Env vars:
  LINKEDIN_CLIENT_ID
  LINKEDIN_CLIENT_SECRET
  LINKEDIN_REDIRECT_URI   default http://localhost:8080/callback
  LINKEDIN_SCOPE          default w_member_social
  LINKEDIN_ACCESS_TOKEN   optional override; if set (and not a TODO), used directly
  LINKEDIN_TOKEN_PATH     token cache path, default credentials/linkedin_token.json
"""

import http.server
import json
import os
import time
import urllib.parse
import webbrowser

import requests

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


def _token_path():
    return os.environ.get("LINKEDIN_TOKEN_PATH", "credentials/linkedin_token.json")


def _redirect_uri():
    return os.environ.get("LINKEDIN_REDIRECT_URI", "http://localhost:8080/callback")


def _scope():
    return os.environ.get("LINKEDIN_SCOPE", "w_member_social")


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    code = None
    error = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            _CallbackHandler.code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"LinkedIn authorization complete. You can close this tab.")
        else:
            _CallbackHandler.error = params.get("error_description", ["unknown error"])[0]
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization failed.")

    def log_message(self, *args):
        pass


def _run_consent_flow(client_id, client_secret):
    redirect_uri = _redirect_uri()
    parsed = urllib.parse.urlparse(redirect_uri)
    host, port = parsed.hostname or "localhost", parsed.port or 8080

    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": _scope(),
        "state": str(int(time.time())),
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(auth_params)
    print(f"Opening browser for LinkedIn consent:\n{url}")
    webbrowser.open(url)

    server = http.server.HTTPServer((host, port), _CallbackHandler)
    server.handle_request()  # serve exactly the callback request

    if _CallbackHandler.error:
        raise RuntimeError(f"LinkedIn consent failed: {_CallbackHandler.error}")
    if not _CallbackHandler.code:
        raise RuntimeError("No authorization code returned by LinkedIn")

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": _CallbackHandler.code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    data["obtained_at"] = int(time.time())
    return data


def load_access_token():
    """Return a valid LinkedIn access token, running consent if needed."""
    override = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if override and not override.startswith("TODO"):
        return override

    token_path = _token_path()
    if os.path.exists(token_path):
        with open(token_path) as f:
            data = json.load(f)
        if data.get("obtained_at", 0) + data.get("expires_in", 0) - 60 > time.time():
            return data["access_token"]

    client_id = os.environ.get("LINKEDIN_CLIENT_ID")
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET not set, and no valid "
            "cached token or LINKEDIN_ACCESS_TOKEN override is available."
        )

    data = _run_consent_flow(client_id, client_secret)
    os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
    with open(token_path, "w") as f:
        json.dump(data, f)
    return data["access_token"]
