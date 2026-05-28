"""Filesystem paths for credentials and OAuth tokens."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

_APP_SUPPORT_NAME = "All Google MCP"
_BUNDLED_CREDENTIALS_NAME = "bundled_credentials.json"


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


def bundled_credentials_sources() -> list[Path]:
    """Shipped OAuth client files (publisher installs once; copied per machine)."""
    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent
    candidates = [
        module_dir / _BUNDLED_CREDENTIALS_NAME,
        project_root / "packaging" / "credentials.json",
    ]
    seen: set[Path] = set()
    out: list[Path] = []
    for p in candidates:
        resolved = p.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if p.is_file():
            out.append(p)
    return out


def ensure_bundled_credentials() -> Path | None:
    """Copy bundled Desktop OAuth client into Application Support if missing."""
    dest = credentials_path()
    if dest.is_file():
        return None
    sources = bundled_credentials_sources()
    if not sources:
        return None
    ensure_support_dir()
    shutil.copy2(sources[0], dest)
    try:
        os.chmod(dest, 0o600)
    except OSError:
        pass
    return dest
