"""Local-only HTTP setup overlay: credentials path, OAuth, token delete, MCP snippet."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from all_google_mcp.app_info import check_for_updates, read_app_version
from all_google_mcp.paths import (
    bundled_credentials_sources,
    credentials_path,
    ensure_bundled_credentials,
    ensure_support_dir,
    support_dir,
    token_path,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

API_KEYS = ("drive", "sheets", "docs", "slides", "gmail")

_auth_lock = threading.Lock()
_auth_state: dict[str, Any] = {
    "running": False,
    "last_error": None,
}


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _wizard_state_path() -> Path:
    return support_dir() / "setup_wizard_state.json"


def _load_wizard_state() -> dict[str, Any]:
    """Persisted checklist: user toggles each API after enabling it in Cloud Console."""
    default_apis = {k: False for k in API_KEYS}
    p = _wizard_state_path()
    if not p.is_file():
        return {"apis": dict(default_apis)}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        apis = dict(default_apis)
        if isinstance(data.get("apis"), dict):
            for k in API_KEYS:
                if k in data["apis"]:
                    apis[k] = bool(data["apis"][k])
        return {"apis": apis}
    except Exception:
        return {"apis": dict(default_apis)}


def _save_wizard_state(state: dict[str, Any]) -> None:
    ensure_support_dir()
    _wizard_state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")


def _bundle_stdio_executable() -> Path | None:
    """If running inside All Google MCP.app, return path to AllGoogleMCPStdio."""
    try:
        root = PROJECT_ROOT.resolve()
    except OSError:
        return None
    for i, part in enumerate(root.parts):
        if part.endswith(".app"):
            base = Path(*root.parts[: i + 1])
            exe = base / "Contents" / "MacOS" / "AllGoogleMCPStdio"
            if exe.is_file():
                return exe
    return None


def _mcp_server_config() -> dict[str, object]:
    bundle_stdio = _bundle_stdio_executable()
    if bundle_stdio is not None:
        return {
            "command": str(bundle_stdio),
            "args": [],
            "env": {},
        }
    root = str(PROJECT_ROOT)
    return {
        "command": "uv",
        "args": ["run", "--directory", root, "python", "-m", "all_google_mcp"],
        "env": {},
    }


def _mcp_json_block() -> str:
    snippet = {"all-google-mcp": _mcp_server_config()}
    return json.dumps(snippet, indent=2)


def _cursor_mcp_path() -> Path:
    return Path.home() / ".cursor" / "mcp.json"


def install_cursor_mcp_config() -> dict[str, object]:
    """Merge all-google-mcp into ~/.cursor/mcp.json; backup existing file first."""
    path = _cursor_mcp_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = _mcp_server_config()
    backup_path: str | None = None

    raw: str | None = None
    if path.is_file():
        raw = path.read_text(encoding="utf-8")
        if len(raw.strip()) > 0:
            ts = time.strftime("%Y%m%d-%H%M%S")
            bak = path.with_name(f"mcp.json.bak-all-google-mcp-{ts}")
            shutil.copy2(path, bak)
            backup_path = str(bak)

    data: dict[str, object] = {}
    if raw and raw.strip():
        try:
            loaded = json.loads(raw)
            if not isinstance(loaded, dict):
                return {"ok": False, "error": "mcp.json is not a JSON object.", "path": str(path)}
            data = loaded
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON in mcp.json: {e}", "path": str(path)}

    servers = data.get("mcpServers")
    if servers is None:
        data["mcpServers"] = {}
        servers = data["mcpServers"]
    if not isinstance(servers, dict):
        return {"ok": False, "error": 'mcpServers must be an object; fix mcp.json manually.', "path": str(path)}

    merged_servers = dict(servers)
    already = merged_servers.get("all-google-mcp") == entry
    merged_servers["all-google-mcp"] = entry
    data["mcpServers"] = merged_servers

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "alreadyConfigured": already,
        "path": str(path),
        "backupPath": backup_path,
        "entry": entry,
    }


def _cursor_has_all_google_mcp() -> bool:
    path = _cursor_mcp_path()
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            return False
        return "all-google-mcp" in servers
    except Exception:
        return False


def _operational_summary(st: dict[str, Any]) -> dict[str, Any]:
    """Dashboard traffic-light states for the status panel."""
    cred_ok = bool(st.get("credentialsPresent"))
    token_ok = bool(st.get("tokenPresent"))
    cursor_ok = bool(st.get("cursorMcpConfigured"))
    oauth_busy = bool(st.get("oauthRunning"))
    ready = cred_ok and token_ok and cursor_ok and not oauth_busy
    if ready:
        overall = "ok"
        overall_label = "Ready for Cursor"
        overall_detail = "Google is connected and Cursor MCP is configured."
    elif not cred_ok:
        overall = "bad"
        overall_label = "App not configured"
        overall_detail = "Missing OAuth client — contact the person who shared this app."
    elif oauth_busy:
        overall = "warn"
        overall_label = "Signing in…"
        overall_detail = "Complete the Google sign-in in your browser."
    elif not token_ok:
        overall = "warn"
        overall_label = "Sign in required"
        overall_detail = "Connect your Google account to use Drive, Docs, Sheets, Slides, and Gmail."
    elif not cursor_ok:
        overall = "warn"
        overall_label = "Connect Cursor"
        overall_detail = "Add All Google MCP to Cursor, then quit and reopen Cursor (⌘Q)."
    else:
        overall = "warn"
        overall_label = "Setup incomplete"
        overall_detail = "Finish the steps below."
    return {
        "overall": overall,
        "overallLabel": overall_label,
        "overallDetail": overall_detail,
        "readyForWork": ready,
        "signals": {
            "app": "ok" if cred_ok else "bad",
            "google": "warn" if oauth_busy else ("ok" if token_ok else "bad"),
            "cursor": "ok" if cursor_ok else "warn",
        },
    }


def _status() -> dict[str, Any]:
    auto_installed = ensure_bundled_credentials()
    c = credentials_path()
    t = token_path()
    bundle = _bundle_stdio_executable()
    bundled_sources = bundled_credentials_sources()
    st = {
        "appVersion": read_app_version(),
        "supportDir": str(support_dir()),
        "credentialsPath": str(c),
        "credentialsPresent": c.is_file(),
        "credentialsBundledInApp": len(bundled_sources) > 0,
        "credentialsAutoInstalled": auto_installed is not None,
        "tokenPath": str(t),
        "tokenPresent": t.is_file(),
        "oauthRunning": bool(_auth_state["running"]),
        "oauthLastError": _auth_state["last_error"],
        "projectRoot": str(PROJECT_ROOT),
        "python": sys.executable,
        "mcpSnippet": _mcp_json_block(),
        "apiEnabledFlags": _load_wizard_state()["apis"],
        "cursorMcpPath": str(_cursor_mcp_path()),
        "usingBundledStdio": bundle is not None,
        "bundledStdioPath": str(bundle) if bundle else None,
        "cursorMcpConfigured": _cursor_has_all_google_mcp(),
    }
    if t.is_file():
        try:
            raw = json.loads(t.read_text(encoding="utf-8"))
            st["tokenHasRefresh"] = bool(raw.get("refresh_token"))
        except Exception:
            st["tokenHasRefresh"] = False
    st.update(_operational_summary(st))
    return st


def _delete_token() -> None:
    p = token_path()
    if p.is_file():
        p.unlink()


def _start_oauth_thread() -> dict[str, str | bool]:
    with _auth_lock:
        if _auth_state["running"]:
            return {"ok": False, "error": "Sign-in already in progress. Finish the browser flow first."}
        _auth_state["running"] = True
        _auth_state["last_error"] = None

    def run() -> None:
        try:
            from all_google_mcp.google_auth import run_oauth_flow

            run_oauth_flow()
        except Exception as e:
            _auth_state["last_error"] = str(e)
        finally:
            _auth_state["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


def _app_icon_path() -> Path:
    """Same artwork as Google MCP.app (mickey-icon.png) — AppIcon bundle + setup header."""
    return Path(__file__).resolve().parent / "app_icon.png"


def _setup_page_html() -> str:
    p = Path(__file__).resolve().parent / "setup_overlay.html"
    return p.read_text(encoding="utf-8")


PAGE = _setup_page_html()


class Handler(BaseHTTPRequestHandler):
    server_version = "AllGoogleMCPSetup/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: dict[str, object], code: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path in ("/app_icon.png", "/icon.png", "/favicon.ico"):
            icon = _app_icon_path()
            if icon.is_file():
                self._send(200, icon.read_bytes(), "image/png")
            else:
                self.send_error(404)
            return
        if path == "/api/status":
            self._json(_status())
            return
        if path == "/api/check-updates":
            # SECURITY-REVIEW: outbound HTTPS to GitHub releases API (fixed host, no user-controlled URL).
            self._json(check_for_updates())
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""

        if path == "/api/toggle-api":
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
                api = str(body.get("api", "")).lower().strip()
                enabled = bool(body.get("enabled"))
                if api not in API_KEYS:
                    self._json({"ok": False, "error": "invalid api"}, 400)
                    return
                st = _load_wizard_state()
                st["apis"][api] = enabled
                _save_wizard_state(st)
                self._json({"ok": True, "apis": st["apis"]})
            except json.JSONDecodeError as e:
                self._json({"ok": False, "error": str(e)}, 400)
            return

        if path == "/api/oauth-start":
            self._json(_start_oauth_thread())
            return
        if path == "/api/delete-token":
            try:
                _delete_token()
                self._json({"ok": True})
            except OSError as e:
                self._json({"ok": False, "error": str(e)}, 500)
            return
        if path == "/api/open-support-folder":
            ensure_support_dir()
            d = support_dir()
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(d)])
            elif sys.platform.startswith("win"):
                os.startfile(str(d))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(d)])
            self._json({"ok": True})
            return
        if path == "/api/install-cursor-mcp":
            try:
                result = install_cursor_mcp_config()
                code = 200 if result.get("ok") else 400
                self._json(result, code)  # type: ignore[arg-type]
            except OSError as e:
                self._json({"ok": False, "error": str(e)}, 500)
            return
        self.send_error(404)


def _open_setup_url(url: str) -> None:
    """Fallback: open the setup page in the default browser."""
    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except OSError:
            pass
    try:
        webbrowser.open(url)
    except Exception:
        pass


def _open_native_window(url: str) -> bool:
    """Show setup UI in a native macOS window (WKWebView via pywebview)."""
    try:
        import webview
    except ImportError:
        return False

    icon = _app_icon_path()
    kwargs: dict[str, object] = {
        "title": "All Google MCP",
        "url": url,
        "width": 400,
        "height": 760,
        "min_size": (360, 540),
        "resizable": True,
        "background_color": "#0a0a0b",
        "text_select": True,
    }
    if icon.is_file():
        kwargs["icon"] = str(icon)

    try:
        webview.create_window(**kwargs)  # type: ignore[arg-type]
        webview.start(debug=False)
        return True
    except Exception as e:
        print(f"Native window unavailable: {e}", flush=True)
        return False


def _run_http_server(server: HTTPServer) -> None:
    try:
        server.serve_forever()
    except Exception:
        pass


def main() -> None:
    ensure_support_dir()
    ensure_bundled_credentials()
    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"

    server_thread = threading.Thread(target=_run_http_server, args=(server,), daemon=True)
    server_thread.start()

    opened_native = _open_native_window(url)
    if not opened_native:
        print(f"All Google MCP: {url}", flush=True)
        print("Opening in your browser — keep this app running for live status.", flush=True)
        _open_setup_url(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

    server.shutdown()
    server.server_close()


if __name__ == "__main__":
    main()
