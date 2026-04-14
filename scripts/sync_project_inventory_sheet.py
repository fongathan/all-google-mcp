#!/usr/bin/env python3
"""
Push project_inventory_full.csv to a Google Sheet and reapply formatting.

Uses the same OAuth as All Google MCP:
  ~/Library/Application Support/All Google MCP/credentials.json + token.json

Run from the all-google-mcp repo:
  uv run python scripts/sync_project_inventory_sheet.py

Override CSV path:
  PROJECT_INVENTORY_CSV=/path/to/project_inventory_full.csv uv run python scripts/sync_project_inventory_sheet.py
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from all_google_mcp.google_auth import build_service, load_credentials  # noqa: E402

_DEFAULT_CSV = Path(
    "/Users/jonathan.fong/Documents/Disney Employee Efficiency/project_inventory_full.csv"
)
CSV_PATH = Path(os.environ.get("PROJECT_INVENTORY_CSV", str(_DEFAULT_CSV))).expanduser()
SPREADSHEET_ID = os.environ.get(
    "PROJECT_INVENTORY_SPREADSHEET_ID",
    "1j0UTUIJwVMH1TX2hcS6R_q1y9VVFq7d3Z5bjg31izuY",
)


def main() -> None:
    if not CSV_PATH.is_file():
        raise SystemExit(f"Missing CSV: {CSV_PATH}")

    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        lines = list(csv.reader(f))
    row_count = len(lines)
    col_count = 7
    sheet_id = 0

    creds = load_credentials()
    sheets = build_service("sheets", "v4", creds)

    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A1",
        valueInputOption="USER_ENTERED",
        body={"values": lines},
    ).execute()

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
    sheets.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": requests}).execute()
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
        sheets.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": zebra}).execute()

    print(f"Synced {row_count - 1} projects to sheet {SPREADSHEET_ID}")


if __name__ == "__main__":
    main()
