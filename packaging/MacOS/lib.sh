#!/bin/bash
# Shared launcher helpers for All Google MCP.app (relocatable; no $HOME uv cache).

show_launch_error() {
  local msg="$1"
  echo "All Google MCP: $msg" >&2
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display alert \"All Google MCP\" message \"${msg//\"/\\\"}\" as critical" >/dev/null 2>&1 || true
  fi
}

resolve_bundled_python() {
  local proj="$1"
  local py=""

  # Prefer venv interpreter only when the symlink target still exists (same install path).
  if [[ -x "$proj/.venv/bin/python" ]]; then
    py="$proj/.venv/bin/python"
    if "$py" -c "pass" >/dev/null 2>&1; then
      printf '%s\n' "$py"
      return 0
    fi
  fi

  # Shipped CPython inside the app bundle (survives unzip / move).
  if [[ -d "$proj/.python" ]]; then
    local candidate
    for candidate in "$proj"/.python/cpython-*/bin/python3.[0-9][0-9]; do
      if [[ -f "$candidate" && -x "$candidate" ]]; then
        py="$candidate"
        break
      fi
    done
    if [[ -n "$py" ]]; then
      printf '%s\n' "$py"
      return 0
    fi
  fi

  return 1
}

run_all_google_mcp() {
  local here proj py
  here="$(cd "$(dirname "$0")" && pwd)"
  proj="$(cd "$here/../Resources/all-google-mcp" && pwd)"
  export PATH="/opt/homebrew/bin:/usr/local/bin:${HOME}/.local/bin:${PATH}"

  if ! py="$(resolve_bundled_python "$proj")"; then
    show_launch_error "This copy of the app is missing its bundled Python. Download the latest release zip from GitHub or rebuild with build-all-google-mcp-app.sh."
    return 1
  fi

  export VIRTUAL_ENV="$proj/.venv"
  cd "$proj" || return 1
  exec "$py" -m all_google_mcp "$@"
}
