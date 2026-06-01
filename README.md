# All Google MCP

**Please contact [Jonathan.Fong@disney.com](mailto:Jonathan.Fong@disney.com) for any help or questions.**

** **NOTE:** since this is not an official app and I don't have a developer account, go to **System Settings**, **Privacy & Security**, and then click **"Open Anyway"** to get the app to launch" 

Python [FastMCP](https://github.com/jlowin/fastmcp) server that talks to **Google Drive, Docs, Sheets, Slides, and Gmail** through the official Google APIs—no subprocess bridge.

## Install (macOS, team build)

Download and install the app first (**no GitHub sign-in required**):

**[Releases → All-Google-MCP-mac.zip](https://github.com/fongathan/all-google-mcp/releases/latest)**

1. Unzip and drag **All Google MCP.app** into **Applications**.
2. **Control-click → Open** on first launch (unsigned app).
3. Open the app — the setup wizard opens in your browser.

Then in the wizard: **Sign in with Google** → **Add to Cursor** → quit Cursor (**⌘Q**) and reopen.

You do **not** need your own Google Cloud project for the team build—the publisher’s OAuth app is bundled. Each person still signs in with **their own** Google account; sessions are stored as `token.json` on that Mac only.

## Quick start (manual / developers)

1. Open **All Google MCP.app** (or run `uv run python -m all_google_mcp setup`) and follow the overlay.
2. In **Cursor → MCP**, set **command** to the **stdio launcher** inside the app bundle (not the GUI launcher):
   - `/Applications/All Google MCP.app/Contents/MacOS/AllGoogleMCPStdio`
   - or `~/Applications/All Google MCP.app/Contents/MacOS/AllGoogleMCPStdio` if you only installed under your home folder.
3. Leave **`args` empty** (or omit). Restart Cursor.

The GUI entry point **`AllGoogleMCP`** opens the setup overlay; **`AllGoogleMCPStdio`** runs the MCP server on stdio for Cursor.

## CLI

- MCP (stdio): `uv run python -m all_google_mcp`
- OAuth sign-in: `uv run python -m all_google_mcp auth`
- Setup overlay: `uv run python -m all_google_mcp setup`

## Config

- Default folder: `~/Library/Application Support/All Google MCP/`
- Team builds copy bundled OAuth into `credentials.json` on first run. Advanced users can supply their own Desktop client (`credentials.json.example` shows the shape) or set `ALL_GOOGLE_MCP_CREDENTIALS`.
- Tokens are stored as `token.json` in the same folder (override with `ALL_GOOGLE_MCP_TOKEN`).
- Override the whole config directory with `ALL_GOOGLE_MCP_HOME`.

**Publisher:** add `all_google_mcp/bundled_credentials.json` (never commit it—see `.gitignore`) before building the `.app`.

## macOS app bundle

From the parent folder (`AI Tools`), run:

```bash
./build-all-google-mcp-app.sh
```

Then open **All Google MCP.app**. The bundle uses the **same `AppIcon.icns` and in-app logo** as **Google MCP.app** (Dock icon + setup wizard header / favicon). The build script copies `AppIcon.icns` from the installed Google MCP app when needed, and copies `mickey-icon.png` to `all_google_mcp/app_icon.png` if that file is missing.

The setup wizard (`python -m all_google_mcp setup`) is styled with a **Midnight Ops**–inspired dark shell: grid background, violet/cyan glows, gradient headline, and pill buttons. The bundle copies this project into `Contents/Resources/all-google-mcp/` and runs `uv sync`.

## Tools (summary)

- **Health:** `all_google_health`
- **Drive:** `drive_list_files`, `drive_get_file_metadata`, `drive_create_google_file`
- **Sheets:** `sheets_get_values`, `sheets_update_values`, `sheets_append_rows`
- **Docs:** `docs_get_document`, `docs_insert_text`
- **Slides:** `slides_get_presentation`
- **Gmail:** `gmail_send_email`, `gmail_search_messages`, `gmail_get_message`

## Project inventory sheet (optional)

The **Disney Employee Efficiency** repo keeps `project_inventory_full.csv`. To push it to the team Sheet with formatting (same OAuth as this MCP):

```bash
cd "/path/to/AI Tools/all-google-mcp"
uv run python scripts/sync_project_inventory_sheet.py
```

Override CSV path: `PROJECT_INVENTORY_CSV=/path/to/project_inventory_full.csv`. Override spreadsheet: `PROJECT_INVENTORY_SPREADSHEET_ID=...`.
