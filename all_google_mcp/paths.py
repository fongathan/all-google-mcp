"""Filesystem paths for credentials and OAuth tokens."""

from __future__ import annotations

import os
from pathlib import Path

_APP_SUPPORT_NAME = "All Google MCP"


def support_dir() -> Path:
    base = os.environ.get("ALL_GOOGLE_MCP_HOME")
    if base:
        return Path(base).expanduser().resolve()
    return Path.home() / "Library" / "Application Support" / _APP_SUPPORT_NAME


def credentials_path() -> Path:
    env = os.environ.get("ALL_GOOGLE_MCP_CREDENTIALS")
    if env:
        return Path(env).expanduser().resolve()
    return support_dir() / "credentials.json"


def token_path() -> Path:
    env = os.environ.get("ALL_GOOGLE_MCP_TOKEN")
    if env:
        return Path(env).expanduser().resolve()
    return support_dir() / "token.json"


def ensure_support_dir() -> Path:
    d = support_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d
