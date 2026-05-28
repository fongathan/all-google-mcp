"""FastMCP server: Drive, Sheets, Docs, Slides, Gmail via google-api-python-client."""

from __future__ import annotations

import base64
import json
from email.message import EmailMessage
from typing import Any

from fastmcp import FastMCP
from googleapiclient.errors import HttpError

from all_google_mcp.google_auth import (
    AuthConfigurationError,
    NotSignedInError,
    build_service,
    load_credentials,
)
from all_google_mcp.paths import credentials_path, token_path

mcp = FastMCP(
    "All Google MCP",
    instructions=(
        "Unified Google Workspace tools: Drive, Google Docs, Sheets, Slides, and Gmail. "
        "Uses OAuth credentials in ~/Library/Application Support/All Google MCP/ "
        "(credentials.json + token.json)."
    ),
)


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except HttpError as e:
        try:
            details = json.loads(e.content.decode("utf-8"))
        except Exception:
            details = e.content.decode("utf-8", errors="replace")
        return _json({"ok": False, "httpError": e.reason, "status": e.resp.status, "details": details})
    except (AuthConfigurationError, NotSignedInError) as e:
        return _json({"ok": False, "error": str(e)})
    except Exception as e:
        return _json({"ok": False, "error": str(e)})


def _creds_and_services():
    creds = load_credentials()
    return creds, {
        "drive": build_service("drive", "v3", creds),
        "sheets": build_service("sheets", "v4", creds),
        "docs": build_service("docs", "v1", creds),
        "slides": build_service("slides", "v1", creds),
        "gmail": build_service("gmail", "v1", creds),
    }


def _extract_doc_plain_text(doc: dict[str, Any]) -> str:
    parts: list[str] = []

    def walk_element(el: dict[str, Any]) -> None:
        if "paragraph" in el:
            for pe in el["paragraph"].get("elements", []):
                tr = pe.get("textRun")
                if tr and "content" in tr:
                    parts.append(tr["content"])
        if "table" in el:
            for row in el["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    for c in cell.get("content", []):
                        walk_element(c)
        if "sectionBreak" in el:
            parts.append("\n")

    for el in doc.get("body", {}).get("content", []):
        walk_element(el)
    return "".join(parts)


@mcp.tool()
def all_google_health() -> str:
    """Report credential paths, token presence, and API readiness (no network calls beyond token refresh)."""
    c_path = credentials_path()
    t_path = token_path()
    out: dict[str, Any] = {
        "ok": True,
        "credentialsPath": str(c_path),
        "credentialsPresent": c_path.is_file(),
        "tokenPath": str(t_path),
        "tokenPresent": t_path.is_file(),
    }
    try:
        creds = load_credentials()
        out["signedIn"] = True
        out["tokenExpiry"] = creds.expiry.isoformat() if creds.expiry else None
    except NotSignedInError as e:
        out["signedIn"] = False
        out["authHint"] = str(e)
    except AuthConfigurationError as e:
        out["signedIn"] = False
        out["configError"] = str(e)
    return _json(out)


@mcp.tool()
def drive_list_files(
    folder_id: str = "root",
    mime_type: str | None = None,
    max_results: int = 50,
) -> str:
    """List files in Google Drive. Use folder_id 'root' for My Drive root. Optional mime_type filter."""
    def inner():
        _, sv = _creds_and_services()
        q_parts = [f"'{folder_id}' in parents", "trashed = false"]
        if mime_type:
            q_parts.append(f"mimeType = '{mime_type}'")
        q = " and ".join(q_parts)
        res = (
            sv["drive"]
            .files()
            .list(
                q=q,
                pageSize=min(max(1, max_results), 100),
                fields="files(id,name,mimeType,modifiedTime,size,webViewLink,parents)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        return _json({"ok": True, "files": res.get("files", [])})

    return _call(inner)


@mcp.tool()
def drive_get_file_metadata(file_id: str) -> str:
    """Return metadata for a Drive file by id."""
    def inner():
        _, sv = _creds_and_services()
        meta = (
            sv["drive"]
            .files()
            .get(
                fileId=file_id,
                fields="id,name,mimeType,modifiedTime,size,webViewLink,parents,exportLinks",
                supportsAllDrives=True,
            )
            .execute()
        )
        return _json({"ok": True, "file": meta})

    return _call(inner)


@mcp.tool()
def drive_create_google_file(
    name: str,
    mime_type: str,
    parent_folder_id: str | None = None,
) -> str:
    """Create a native Google file (Doc, Sheet, or Slide deck) in Drive."""
    def inner():
        _, sv = _creds_and_services()
        body: dict[str, Any] = {"name": name, "mimeType": mime_type}
        if parent_folder_id:
            body["parents"] = [parent_folder_id]
        created = sv["drive"].files().create(body=body, fields="id,name,mimeType,webViewLink").execute()
        return _json({"ok": True, "file": created})

    return _call(inner)


@mcp.tool()
def sheets_get_values(spreadsheet_id: str, range_a1: str) -> str:
    """Read a range from a spreadsheet (A1 notation, e.g. 'Sheet1!A1:D10')."""
    def inner():
        _, sv = _creds_and_services()
        res = (
            sv["sheets"]
            .spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_a1)
            .execute()
        )
        return _json({"ok": True, "range": res.get("range"), "values": res.get("values", [])})

    return _call(inner)


@mcp.tool()
def sheets_update_values(
    spreadsheet_id: str,
    range_a1: str,
    values_json: str,
    value_input_option: str = "USER_ENTERED",
) -> str:
    """Write a 2D JSON array of cell values into range_a1. values_json e.g. '[["A","B"],[1,2]]'."""
    def inner():
        values = json.loads(values_json)
        if not isinstance(values, list):
            raise ValueError("values_json must be a JSON array of rows")
        _, sv = _creds_and_services()
        body = {"values": values}
        res = (
            sv["sheets"]
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_a1,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
        return _json({"ok": True, "updatedRange": res.get("updatedRange"), "updatedCells": res.get("updatedCells")})

    return _call(inner)


@mcp.tool()
def sheets_append_rows(spreadsheet_id: str, range_a1: str, values_json: str) -> str:
    """Append rows (2D JSON array) after the table in range_a1."""
    def inner():
        values = json.loads(values_json)
        _, sv = _creds_and_services()
        body = {"values": values}
        res = (
            sv["sheets"]
            .spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_a1,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
        return _json({"ok": True, "updates": res.get("updates", res)})

    return _call(inner)


@mcp.tool()
def docs_get_document(document_id: str, include_plain_text: bool = True) -> str:
    """Fetch a Google Doc by id. Optionally includes extracted plain text."""
    def inner():
        _, sv = _creds_and_services()
        doc = sv["docs"].documents().get(documentId=document_id).execute()
        out: dict[str, Any] = {"ok": True, "documentId": doc.get("documentId"), "title": doc.get("title")}
        if include_plain_text:
            out["plainText"] = _extract_doc_plain_text(doc)
        else:
            out["document"] = doc
        return _json(out)

    return _call(inner)


@mcp.tool()
def docs_insert_text(document_id: str, text: str, insert_index: int = 1) -> str:
    """Insert text at a character index in the document body (default 1 = after start)."""
    def inner():
        _, sv = _creds_and_services()
        req = {"requests": [{"insertText": {"location": {"index": insert_index}, "text": text}}]}
        res = sv["docs"].documents().batchUpdate(documentId=document_id, body=req).execute()
        return _json({"ok": True, "reply": res})

    return _call(inner)


@mcp.tool()
def slides_get_presentation(presentation_id: str) -> str:
    """Return Slides presentation metadata and per-slide object ids."""
    def inner():
        _, sv = _creds_and_services()
        pr = sv["slides"].presentations().get(presentationId=presentation_id).execute()
        slides_out = [{"objectId": s.get("objectId")} for s in pr.get("slides", [])]
        return _json(
            {
                "ok": True,
                "presentationId": pr.get("presentationId"),
                "title": pr.get("title"),
                "slides": slides_out,
                "webViewLink": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
            }
        )

    return _call(inner)


@mcp.tool()
def gmail_send_email(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    is_html: bool = False,
) -> str:
    """Send email via Gmail API (plain text or HTML)."""
    def inner():
        _, sv = _creds_and_services()
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        if is_html:
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        sent = sv["gmail"].users().messages().send(userId="me", body={"raw": raw}).execute()
        return _json({"ok": True, "id": sent.get("id"), "threadId": sent.get("threadId")})

    return _call(inner)


@mcp.tool()
def gmail_search_messages(query: str, max_results: int = 20) -> str:
    """Search Gmail with Gmail query syntax (same as web search box)."""
    def inner():
        _, sv = _creds_and_services()
        n = min(max(1, max_results), 50)
        lst = sv["gmail"].users().messages().list(userId="me", q=query, maxResults=n).execute()
        mids = [m["id"] for m in lst.get("messages", [])]
        return _json({"ok": True, "messageIds": mids, "resultSizeEstimate": lst.get("resultSizeEstimate")})

    return _call(inner)


@mcp.tool()
def gmail_get_message(message_id: str, message_format: str = "full") -> str:
    """Fetch a single message by id (message_format: minimal | full | raw | metadata)."""
    def inner():
        _, sv = _creds_and_services()
        m = (
            sv["gmail"]
            .users()
            .messages()
            .get(userId="me", id=message_id, format=message_format)
            .execute()
        )
        return _json({"ok": True, "message": m})

    return _call(inner)
