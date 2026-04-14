"""OAuth 2.0 for all Google Workspace APIs used by this MCP server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from all_google_mcp.paths import credentials_path, ensure_support_dir, token_path

# One combined consent for Drive, Docs, Sheets, Slides, Gmail.
SCOPES: list[str] = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
]


class AuthConfigurationError(RuntimeError):
    """credentials.json missing or invalid."""


class NotSignedInError(RuntimeError):
    """token.json missing or refresh failed; user must run OAuth."""


def _load_client_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AuthConfigurationError(
            f"Missing OAuth client file: {path}\n"
            "Download credentials.json from Google Cloud Console (Desktop app) and place it there, "
            "or set ALL_GOOGLE_MCP_CREDENTIALS."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "installed" in raw:
        return {"installed": raw["installed"]}
    if "web" in raw:
        return {"web": raw["web"]}
    raise AuthConfigurationError(
        "credentials.json must contain an 'installed' or 'web' OAuth client block."
    )


def run_oauth_flow() -> None:
    """Interactive browser OAuth; writes token.json."""
    path = credentials_path()
    client_config = _load_client_config(path)
    ensure_support_dir()
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    token_path().write_text(creds.to_json(), encoding="utf-8")
    print(f"Saved OAuth token to {token_path()}", flush=True)


def load_credentials() -> Credentials:
    """Return valid Credentials, refreshing access token when possible."""
    c_path = credentials_path()
    _load_client_config(c_path)  # validate early
    t_path = token_path()
    if not t_path.is_file():
        raise NotSignedInError(
            f"No token at {t_path}. Run: uv run python -m all_google_mcp auth\n"
            "Or use All Google MCP.app → Sign in with Google."
        )
    creds = Credentials.from_authorized_user_file(str(t_path), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            t_path.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise NotSignedInError("Token unusable; delete token.json and sign in again.")
    return creds


def build_service(api_name: str, version: str, creds: Credentials):
    return build(api_name, version, credentials=creds, cache_discovery=False)
