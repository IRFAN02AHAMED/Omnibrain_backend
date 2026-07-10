# app/routes/google/google_sheets_routes.py
# Purpose: Google Sheets API routes for listing sheets, reading values, and getting tab names.

from fastapi import APIRouter, Query

from app.services.google.google_sheets_service import (
    list_google_sheets,
    read_sheet_values,
    get_sheet_tabs,
)

# TODO: Replace `user_id` query parameter with current logged-in user from JWT dependency later.

router = APIRouter(prefix="/google/sheets", tags=["Google Sheets"])


@router.get("/files")
async def sheets_files(
    user_id: int = Query(..., description="User ID"),
    page_size: int = Query(10, description="Number of spreadsheets to return"),
):
    """
    List Google Sheets from Drive.

    Returns spreadsheets filtered by Google Sheets MIME type,
    ordered by most recently modified.

    Example:
        GET /google/sheets/files?user_id=1&page_size=10
    """
    return list_google_sheets(user_id=user_id, page_size=page_size)


@router.get("/{spreadsheet_id}/values")
async def sheets_values(
    spreadsheet_id: str,
    user_id: int = Query(..., description="User ID"),
    range_name: str = Query("Sheet1!A1:Z100", description="Sheet range in A1 notation"),
):
    """
    Read values from a Google Sheet range.

    Returns both raw values (list of rows) and formatted data
    (list of dicts using first row as headers).

    Example:
        GET /google/sheets/SPREADSHEET_ID/values?user_id=1&range_name=Sheet1!A1:Z100
    """
    return read_sheet_values(
        user_id=user_id,
        spreadsheet_id=spreadsheet_id,
        range_name=range_name,
    )


@router.get("/{spreadsheet_id}/tabs")
async def sheets_tabs(
    spreadsheet_id: str,
    user_id: int = Query(..., description="User ID"),
):
    """
    Get sheet tab names for a Google Spreadsheet.

    Returns title, index, and sheetId for each tab.

    Example:
        GET /google/sheets/SPREADSHEET_ID/tabs?user_id=1
    """
    return get_sheet_tabs(user_id=user_id, spreadsheet_id=spreadsheet_id)
