# app/services/google/google_sheets_service.py
# Purpose: Google Sheets API logic for listing sheets, reading values, and getting tab names.

from fastapi import HTTPException

from app.services.google.google_token_store import get_google_account
from app.services.google.google_client_service import get_drive_client, get_sheets_client
from app.services.google.google_helper_service import format_sheet_values


def list_google_sheets(user_id: int, page_size: int = 10) -> dict:
    """
    List Google Sheets from the user's Drive.

    Uses the Drive API to filter files by Google Sheets MIME type.
    Returns id, name, mimeType, webViewLink, and modifiedTime.

    Args:
        user_id: The application user ID.
        page_size: Number of spreadsheets to return (default: 10).

    Returns:
        dict: Dictionary with 'spreadsheets' list and 'count'.
    """
    account = get_google_account(user_id)
    service = get_drive_client(account)

    try:
        drive_query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"

        results = service.files().list(
            q=drive_query,
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        return {"spreadsheets": files, "count": len(files)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Google Sheets: {str(e)}")


def read_sheet_values(
    user_id: int,
    spreadsheet_id: str,
    range_name: str = "Sheet1!A1:Z100",
) -> dict:
    """
    Read values from a specific Google Sheet range.

    Uses the Sheets API to fetch cell values. Returns both the raw values
    (list of rows) and a formatted version (list of dicts using first row as headers).

    Args:
        user_id: The application user ID.
        spreadsheet_id: The Google Sheets spreadsheet ID.
        range_name: The A1 notation range to read (default: "Sheet1!A1:Z100").

    Returns:
        dict: Dictionary with spreadsheet_id, range, raw_values, formatted_data, and row_count.
    """
    account = get_google_account(user_id)
    service = get_sheets_client(account)

    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
        ).execute()

        values = result.get("values", [])
        formatted = format_sheet_values(values)

        return {
            "spreadsheet_id": spreadsheet_id,
            "range": range_name,
            "raw_values": values,
            "formatted_data": formatted,
            "row_count": len(values),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read sheet values: {str(e)}")


def get_sheet_tabs(user_id: int, spreadsheet_id: str) -> dict:
    """
    Get the list of sheet tab names in a Google Spreadsheet.

    Uses the Sheets API to fetch spreadsheet metadata and extract
    the title, index, and sheetId for each tab.

    Args:
        user_id: The application user ID.
        spreadsheet_id: The Google Sheets spreadsheet ID.

    Returns:
        dict: Dictionary with spreadsheet_id, tabs list, and count.
    """
    account = get_google_account(user_id)
    service = get_sheets_client(account)

    try:
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
        ).execute()

        sheets = spreadsheet.get("sheets", [])
        tabs = [
            {
                "title": sheet.get("properties", {}).get("title", ""),
                "index": sheet.get("properties", {}).get("index", 0),
                "sheet_id": sheet.get("properties", {}).get("sheetId", 0),
            }
            for sheet in sheets
        ]

        return {
            "spreadsheet_id": spreadsheet_id,
            "tabs": tabs,
            "count": len(tabs),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sheet tabs: {str(e)}")
