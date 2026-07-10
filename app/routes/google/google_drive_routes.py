# app/routes/google/google_drive_routes.py
# Purpose: Google Drive API routes for listing, searching, and getting file metadata.

from fastapi import APIRouter, Query, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.connected_account import ConnectedAccount
from app.models.user import User

from app.services.google.google_drive_service import (
    list_drive_files,
    search_drive_files,
    get_drive_file_metadata,
    ensure_omnibrain_folders,
    upload_file_to_folder,
)

from app.services.google.google_client_service import get_drive_client_for_user
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

@router.get("/files/me")
async def drive_files_me(
    page_size: int = Query(10, description="Number of files to return"),
    current_user: User = Depends(get_current_user)
):
    """List recent files from Google Drive for the current authenticated user."""
    return list_drive_files(user_id=current_user.id, page_size=page_size)

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

@router.get("/search/me")
async def drive_search_me(
    query: str = Query(..., description="Search query to match against file names"),
    page_size: int = Query(10, description="Number of results to return"),
    current_user: User = Depends(get_current_user)
):
    """Search Google Drive files by name for the current authenticated user."""
    return search_drive_files(user_id=current_user.id, query=query, page_size=page_size)

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


@router.post("/upload")
async def upload_document_to_drive(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document to the user's Google Drive.

    Folder structure:
        My Drive/
        └── OmniBrain AI/
            └── Global Documents/
                └── uploaded file
    """

    # 1. Read uploaded file content
    file_content = await file.read()

    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # 2. Make sure OmniBrain AI folders exist
    folders = await ensure_omnibrain_folders(
        user_id=current_user.id,
        db=db,
    )

    global_folder_id = folders["global_documents_folder_id"]

    # 3. Get Google Drive client for this logged-in user
    drive_service = await get_drive_client_for_user(
        user_id=current_user.id,
        db=db,
    )

    # 4. Upload file to Global Documents folder
    uploaded_file = upload_file_to_folder(
        service=drive_service,
        file_content=file_content,
        file_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        folder_id=global_folder_id,
    )

    return {
        "success": True,
        "message": "File uploaded to Google Drive successfully",
        "data": {
            "file_id": uploaded_file.get("id"),
            "file_name": uploaded_file.get("name"),
            "mime_type": uploaded_file.get("mimeType"),
            "web_view_link": uploaded_file.get("webViewLink"),
            "folder_id": global_folder_id,
            "folder_path": "OmniBrain AI/Global Documents",
        },
    }
