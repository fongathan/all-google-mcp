"""App version and GitHub release update checks."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_GITHUB_REPO = "fongathan/all-google-mcp"
_RELEASES_LATEST = "https://api.github.com/repos/{repo}/releases/latest"


def read_app_version() -> str:
    """Version from the .app Info.plist when bundled, else packaging/Info.plist or pyproject.toml."""
    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent

    plist_candidates = [
        module_dir.parent.parent.parent.parent / "Info.plist",  # …/Contents/Info.plist in .app
        project_root / "packaging" / "Info.plist",
    ]
    for plist in plist_candidates:
        if not plist.is_file():
            continue
        text = plist.read_text(encoding="utf-8", errors="ignore")
        match = re.search(
            r"<key>CFBundleShortVersionString</key>\s*<string>([^<]+)</string>",
            text,
        )
        if match:
            return match.group(1).strip()

    toml = project_root / "pyproject.toml"
    if toml.is_file():
        match = re.search(r'^version\s*=\s*"([^"]+)"', toml.read_text(encoding="utf-8"), re.M)
        if match:
            return match.group(1).strip()
    return "0.0.0"


def _parse_version(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in re.split(r"[.\-]", version.lstrip("vV")):
        if piece.isdigit():
            parts.append(int(piece))
        else:
            break
    return tuple(parts or (0,))


def compare_versions(current: str, latest: str) -> int:
    """Return -1 if current < latest, 0 if equal, 1 if current > latest."""
    a = _parse_version(current)
    b = _parse_version(latest)
    length = max(len(a), len(b))
    a = a + (0,) * (length - len(a))
    b = b + (0,) * (length - len(b))
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def check_for_updates(repo: str = DEFAULT_GITHUB_REPO, timeout: float = 12.0) -> dict[str, Any]:
    """Fetch latest GitHub release; compare to installed app version."""
    current = read_app_version()
    url = _RELEASES_LATEST.format(repo=repo)
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "AllGoogleMCP-Setup",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {
            "ok": False,
            "currentVersion": current,
            "error": f"GitHub returned HTTP {e.code}",
        }
    except urllib.error.URLError as e:
        return {
            "ok": False,
            "currentVersion": current,
            "error": "Could not reach GitHub. Check your network connection.",
            "detail": str(e.reason) if getattr(e, "reason", None) else str(e),
        }
    except Exception as e:
        return {"ok": False, "currentVersion": current, "error": "Update check failed.", "detail": str(e)}

    tag = str(payload.get("tag_name") or "").lstrip("v")
    html_url = str(payload.get("html_url") or f"https://github.com/{repo}/releases/latest")
    name = str(payload.get("name") or payload.get("tag_name") or "")
    published = str(payload.get("published_at") or "")

    download_url = html_url
    assets = payload.get("assets")
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            asset_name = str(asset.get("name") or "")
            if asset_name.endswith(".zip"):
                download_url = str(asset.get("browser_download_url") or download_url)
                break

    cmp = compare_versions(current, tag)
    return {
        "ok": True,
        "currentVersion": current,
        "latestVersion": tag,
        "latestName": name,
        "publishedAt": published,
        "releaseUrl": html_url,
        "downloadUrl": download_url,
        "updateAvailable": cmp < 0,
        "upToDate": cmp >= 0,
    }
