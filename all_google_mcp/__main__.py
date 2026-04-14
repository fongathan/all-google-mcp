"""Entry: MCP stdio, OAuth, or setup UI."""

from __future__ import annotations

import sys


def run_mcp() -> None:
    from all_google_mcp.mcp_server import mcp

    mcp.run()


def run_auth() -> None:
    from all_google_mcp.google_auth import run_oauth_flow

    run_oauth_flow()


def run_setup() -> None:
    from all_google_mcp.setup_ui import main

    main()


def main() -> None:
    if len(sys.argv) < 2:
        run_mcp()
        return
    cmd = sys.argv[1].lower()
    if cmd in ("auth", "login", "signin"):
        run_auth()
    elif cmd in ("setup", "ui", "panel"):
        run_setup()
    elif cmd in ("--help", "-h", "help"):
        print(
            "Usage:\n"
            "  python -m all_google_mcp              # MCP server (stdio)\n"
            "  python -m all_google_mcp auth         # Browser OAuth\n"
            "  python -m all_google_mcp setup        # Setup overlay UI\n",
            flush=True,
        )
    else:
        print(f"Unknown command: {sys.argv[1]!r}. Try: auth | setup", file=sys.stderr, flush=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
