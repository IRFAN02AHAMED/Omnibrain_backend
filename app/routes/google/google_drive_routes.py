# app/routes/google/google_drive_routes.py
# Purpose: Google Drive API routes for listing, searching, and getting file metadata.

from fastapi import APIRouter, Query

from app.services.google.google_drive_service import (
    list_drive_files,
    search_drive_files,
    get_drive_file_metadata,
)

# TODO: Replace `user_id` query parameter with current logged-in user from JWT dependency later.

router = APIRouter(prefix="/google/drive", tags=["Google Drive"])


@router.get("/files")
async def drive_files(
    user_id: int = Query(..., description="User ID"),
    page_size: int = Query(10, description="Number of files to return"),
):
    """
    List recent files from Google Drive.

    Returns files ordered by most recently modified.

    Example:
        GET /google/drive/files?user_id=1&page_size=10
    """
    return list_drive_files(user_id=user_id, page_size=page_size)


@router.get("/search")
async def drive_search(
    user_id: int = Query(..., description="User ID"),
    query: str = Query(..., description="Search query to match against file names"),
    page_size: int = Query(10, description="Number of results to return"),
):
    """
    Search Google Drive files by name.

    Example:
        GET /google/drive/search?user_id=1&query=project&page_size=10
    """
    return search_drive_files(user_id=user_id, query=query, page_size=page_size)


@router.get("/files/{file_id}")
async def drive_file_metadata(
    file_id: str,
    user_id: int = Query(..., description="User ID"),
):
    """
    Get metadata for a specific Google Drive file.

    Example:
        GET /google/drive/files/FILE_ID?user_id=1
    """
    return get_drive_file_metadata(user_id=user_id, file_id=file_id)
