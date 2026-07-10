# app/routes/google/google_drive_routes.py
# Purpose: Google Drive API routes for listing, searching, and getting file metadata.

from fastapi import APIRouter, Query, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

from app.services.google.google_drive_service import (
    list_drive_files,
    search_drive_files,
    get_drive_file_metadata,
    list_drive_files_db,
    search_drive_files_db,
    get_drive_file_metadata_db,
    ensure_omnibrain_folders,
    upload_file_to_folder,
)

from app.services.google.google_client_service import get_drive_client_for_user
from app.repositories.connected_account_repository import ConnectedAccountRepository

router = APIRouter(prefix="/google/drive", tags=["Google Drive"])


# ============================================================
# PRODUCTION DB-BACKED ROUTES (JWT REQUIRED)
# ============================================================

@router.get("/files/me")
async def drive_files_me(
    page_size: int = Query(10, description="Number of files to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List recent files from Google Drive (Production DB-backed flow)."""
    return await list_drive_files_db(user_id=current_user.id, db=db, page_size=page_size)


@router.get("/search/me")
async def drive_search_me(
    query: str = Query(..., description="Search query to match against file names"),
    page_size: int = Query(10, description="Number of results to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search Google Drive files by name (Production DB-backed flow)."""
    return await search_drive_files_db(user_id=current_user.id, db=db, query=query, page_size=page_size)


@router.get("/files/{file_id}/me")
async def drive_file_metadata_me(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get metadata for a specific Google Drive file (Production DB-backed flow)."""
    return await get_drive_file_metadata_db(user_id=current_user.id, db=db, file_id=file_id)


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
    file_content = await file.read()

    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    folders = await ensure_omnibrain_folders(user_id=current_user.id, db=db)
    global_folder_id = folders["global_documents_folder_id"]

    drive_service = await get_drive_client_for_user(user_id=current_user.id, db=db)

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


# ============================================================
# DEBUG ROUTES
# ============================================================

@router.get("/debug/folders/me")
async def debug_drive_folders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Debug route to manually trigger folder creation and inspect metadata."""
    try:
        folders = await ensure_omnibrain_folders(user_id=current_user.id, db=db)
        return {"success": True, "folders": folders}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/debug/account/me")
async def debug_account_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Debug route to view connected account metadata."""
    repo = ConnectedAccountRepository(db)
    account = await repo.get_by_user_id_and_provider(current_user.id, "google")
    
    if not account:
        return {"connected": False}
        
    return {
        "connected": True,
        "metadata": account.metadata_,
        "scopes": account.scopes
    }


# ============================================================
# OLD TESTING ROUTES (Require ?user_id=1)
# ============================================================

@router.get("/files")
async def drive_files(
    user_id: int = Query(..., description="User ID"),
    page_size: int = Query(10, description="Number of files to return"),
):
    """List recent files from Google Drive (Old testing)."""
    return list_drive_files(user_id=user_id, page_size=page_size)


@router.get("/search")
async def drive_search(
    user_id: int = Query(..., description="User ID"),
    query: str = Query(..., description="Search query to match against file names"),
    page_size: int = Query(10, description="Number of results to return"),
):
    """Search Google Drive files by name (Old testing)."""
    return search_drive_files(user_id=user_id, query=query, page_size=page_size)


@router.get("/files/{file_id}")
async def drive_file_metadata(
    file_id: str,
    user_id: int = Query(..., description="User ID"),
):
    """Get metadata for a specific Google Drive file (Old testing)."""
    return get_drive_file_metadata(user_id=user_id, file_id=file_id)
