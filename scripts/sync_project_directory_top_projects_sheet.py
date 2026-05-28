#!/usr/bin/env python3
"""
Create or update the "Project Directory - Top Projects in Cursor" Google Sheet
with the same styling as sync_project_inventory_sheet.py.

CSV default:
  ~/Documents/Directory/project_directory_top_projects_in_cursor.csv

Target spreadsheet:
  PROJECT_DIRECTORY_TOP_SPREADSHEET_ID if set; else parse ID from
  ~/Documents/Directory/PROJECT_DIRECTORY_TOP_PROJECTS_SHEET.md if present;
  else create a new spreadsheet and write that markdown file.

Run from all-google-mcp:
  uv run python scripts/sync_project_directory_top_projects_sheet.py
"""
from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from all_google_mcp.google_auth import build_service, load_credentials  # noqa: E402

TITLE = "Project Directory - Top Projects in Cursor"
_DEFAULT_CSV = Path(
    "/Users/jonathan.fong/Documents/Directory/project_directory_top_projects_in_cursor.csv"
)
CSV_PATH = Path(os.environ.get("PROJECT_DIRECTORY_TOP_CSV", str(_DEFAULT_CSV))).expanduser()
_DIRECTORY_MD = Path(
    "/Users/jonathan.fong/Documents/Directory/PROJECT_DIRECTORY_TOP_PROJECTS_SHEET.md"
)
SHEET_LINK_RE = re.compile(
    r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", re.MULTILINE
)


def _read_spreadsheet_id_from_md(path: Path) -> str | None:
    if not path.is_file():
        return None
    m = SHEET_LINK_RE.search(path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _formatting_requests(row_count: int, col_count: int, sheet_id: int) -> list:
    requests: list = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": col_count,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.16, "green": 0.20, "blue": 0.25},
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                            "fontSize": 11,
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP",
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": row_count,
                    "startColumnIndex": 0,
                    "endColumnIndex": col_count,
                },
                "cell": {
                    "userEnteredFormat": {
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP",
                    }
                },
                "fields": "userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy",
            }
        },
    ]
    for i, w in enumerate([180, 200, 280, 320, 200, 70, 260]):
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": i,
                        "endIndex": i + 1,
                    },
                    "properties": {"pixelSize": w},
                    "fields": "pixelSize",
                }
            }
        )
    requests.extend(
        [
            {
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": row_count,
                        "startColumnIndex": 0,
                        "endColumnIndex": col_count,
                    },
                    "top": {"style": "SOLID", "width": 1, "color": {"red": 0.85, "green": 0.85, "blue": 0.85}},
                    "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0.85, "green": 0.85, "blue": 0.85}},
                    "left": {"style": "SOLID", "width": 1, "color": {"red": 0.85, "green": 0.85, "blue": 0.85}},
                    "right": {"style": "SOLID", "width": 1, "color": {"red": 0.85, "green": 0.85, "blue": 0.85}},
                    "innerHorizontal": {"style": "SOLID", "width": 1, "color": {"red": 0.92, "green": 0.92, "blue": 0.92}},
                    "innerVertical": {"style": "SOLID", "width": 1, "color": {"red": 0.92, "green": 0.92, "blue": 0.92}},
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
                    "properties": {"pixelSize": 44},
                    "fields": "pixelSize",
                }
            },
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": row_count,
                            "startColumnIndex": 0,
                            "endColumnIndex": col_count,
                        }
                    }
                }
            },
        ]
    )
    return requests


def main() -> None:
    if not CSV_PATH.is_file():
        raise SystemExit(f"Missing CSV: {CSV_PATH}")

    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        lines = list(csv.reader(f))
    row_count = len(lines)
    col_count = 7

    creds = load_credentials()
    sheets = build_service("sheets", "v4", creds)

    spreadsheet_id = os.environ.get("PROJECT_DIRECTORY_TOP_SPREADSHEET_ID", "").strip()
    if not spreadsheet_id:
        spreadsheet_id = _read_spreadsheet_id_from_md(_DIRECTORY_MD) or ""

    created = False
    if not spreadsheet_id:
        created_body = sheets.spreadsheets().create(
            body={"properties": {"title": TITLE}, "sheets": [{"properties": {"title": "Sheet1"}}]}
        ).execute()
        spreadsheet_id = created_body["spreadsheetId"]
        created = True

    meta = (
        sheets.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets(properties(sheetId,title))")
        .execute()
    )
    first = (meta.get("sheets") or [{}])[0]
    sheet_id = int(first.get("properties", {}).get("sheetId", 0))

    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A1",
        valueInputOption="USER_ENTERED",
        body={"values": lines},
    ).execute()

    if created:
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"updateSpreadsheetProperties": {"properties": {"title": TITLE}, "fields": "title"}}]},
        ).execute()

    requests = _formatting_requests(row_count, col_count, sheet_id)
    sheets.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()

    zebra = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": r,
                    "endRowIndex": r + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": col_count,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.98, "green": 0.98, "blue": 0.99}
                    }
                },
                "fields": "userEnteredFormat.backgroundColor",
            }
        }
        for r in range(2, row_count, 2)
    ]
    if zebra:
        sheets.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": zebra}).execute()

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    _DIRECTORY_MD.parent.mkdir(parents=True, exist_ok=True)
    _DIRECTORY_MD.write_text(
        "\n".join(
            [
                f"# {TITLE}",
                "",
                f"**Live sheet:** [{url}]({url})",
                "",
                "Styling matches the main project inventory sheet (header row, column widths, borders, filters, zebra striping).",
                "",
                "Source CSV (edit then re-sync):",
                f"`{CSV_PATH}`",
                "",
                "Re-sync after CSV changes:",
                "```bash",
                'cd "/Users/jonathan.fong/Documents/AI Tools/all-google-mcp"',
                "uv run python scripts/sync_project_directory_top_projects_sheet.py",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    action = "Created" if created else "Updated"
    print(f"{action} sheet {spreadsheet_id} ({row_count - 1} data rows)")
    print(url)
    print(f"Wrote workspace pointer: {_DIRECTORY_MD}")


if __name__ == "__main__":
    main()
