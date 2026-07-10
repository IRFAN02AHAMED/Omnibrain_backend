# app/services/google/google_drive_service.py
# Purpose: Google Drive API logic for listing, searching, and getting file metadata.

from fastapi import HTTPException

from app.services.google.google_token_store import get_google_account
from app.services.google.google_client_service import get_drive_client


def list_drive_files(user_id: int, page_size: int = 10) -> dict:
    """
    List recent files from the user's Google Drive.

    Returns files ordered by most recently modified, including
    id, name, mimeType, webViewLink, modifiedTime, and size.

    Args:
        user_id: The application user ID.
        page_size: Number of files to return (default: 10).

    Returns:
        dict: Dictionary with 'files' list and 'count'.
    """
    account = get_google_account(user_id)
    service = get_drive_client(account)

    try:
        results = service.files().list(
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime, size)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        return {"files": files, "count": len(files)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Drive files: {str(e)}")


def search_drive_files(user_id: int, query: str, page_size: int = 10) -> dict:
    """
    Search Google Drive files by file name.

    Uses the Drive API query syntax: name contains '<query>' and trashed=false.

    Args:
        user_id: The application user ID.
        query: Search text to match against file names.
        page_size: Number of results to return (default: 10).

    Returns:
        dict: Dictionary with 'query', 'files' list, and 'count'.
    """
    account = get_google_account(user_id)
    service = get_drive_client(account)

    try:
        drive_query = f"name contains '{query}' and trashed=false"

        results = service.files().list(
            q=drive_query,
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime, size)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        return {"query": query, "files": files, "count": len(files)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search Drive files: {str(e)}")


def get_drive_file_metadata(user_id: int, file_id: str) -> dict:
    """
    Get metadata for a single Google Drive file.

    Returns detailed metadata including id, name, mimeType, webViewLink,
    modifiedTime, size, owners, and createdTime.

    Args:
        user_id: The application user ID.
        file_id: The Google Drive file ID.

    Returns:
        dict: File metadata from Drive API.
    """
    account = get_google_account(user_id)
    service = get_drive_client(account)

    try:
        file_metadata = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, webViewLink, modifiedTime, size, owners, createdTime",
        ).execute()

        return file_metadata

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file metadata: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# NEW FUNCTIONS — Folder Creation, Upload, List, Download, Export
# These are used by the production document flows.
# ─────────────────────────────────────────────────────────────────────────────

import io
from googleapiclient.http import MediaIoBaseUpload
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.google.google_client_service import get_drive_client_for_user
from app.repositories.connected_account_repository import ConnectedAccountRepository
from app.core.logger import logger


def find_folder_by_name(service, name: str, parent_id: str | None = None) -> str | None:
    """
    Search for a folder by name (and optionally parent).

    Args:
        service: Google Drive API service instance.
        name: Folder name to search for.
        parent_id: Optional parent folder ID to scope the search.

    Returns:
        Folder ID if found, None otherwise.
    """
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=1,
    ).execute()

    files = results.get("files", [])
    if files:
        return files[0]["id"]
    return None


def create_folder(service, name: str, parent_id: str | None = None) -> str:
    """
    Create a folder in Google Drive.

    Args:
        service: Google Drive API service instance.
        name: Name of the folder to create.
        parent_id: Optional parent folder ID.

    Returns:
        The created folder's ID.
    """
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        file_metadata["parents"] = [parent_id]

    folder = service.files().create(
        body=file_metadata,
        fields="id",
    ).execute()

    logger.info(f"[GoogleDrive] Created folder '{name}' id={folder['id']}")
    return folder["id"]


async def ensure_omnibrain_folders(user_id: int, db: AsyncSession) -> dict:
    """
    Ensure the OmniBrain AI folder structure exists in the user's Google Drive.

    Structure:
        My Drive/
        └── OmniBrain AI/
            ├── Global Documents/
            └── Chat Documents/

    Creates missing folders and stores folder IDs in connected_accounts.metadata.

    Args:
        user_id: Application user ID.
        db: Async database session.

    Returns:
        dict with root_folder_id, global_documents_folder_id, chat_documents_folder_id.
    """
    # Check if folder IDs are already cached in metadata
    repo = ConnectedAccountRepository(db)
    account = await repo.get_by_user_id(user_id, provider="google")

    if account and account.metadata_:
        meta = account.metadata_
        if all(k in meta for k in ["root_folder_id", "global_documents_folder_id", "chat_documents_folder_id"]):
            logger.debug(f"[GoogleDrive] Folder IDs cached for user_id={user_id}")
            return meta

    # Build Drive client from DB credentials
    service = await get_drive_client_for_user(user_id, db)

    # 1. Find or create root folder: "OmniBrain AI"
    root_id = find_folder_by_name(service, "OmniBrain AI")
    if not root_id:
        root_id = create_folder(service, "OmniBrain AI")

    # 2. Find or create "Global Documents" inside root
    global_id = find_folder_by_name(service, "Global Documents", parent_id=root_id)
    if not global_id:
        global_id = create_folder(service, "Global Documents", parent_id=root_id)

    # 3. Find or create "Chat Documents" inside root
    chat_id = find_folder_by_name(service, "Chat Documents", parent_id=root_id)
    if not chat_id:
        chat_id = create_folder(service, "Chat Documents", parent_id=root_id)

    # Store folder IDs in connected_accounts.metadata
    folder_ids = {
        "root_folder_id": root_id,
        "global_documents_folder_id": global_id,
        "chat_documents_folder_id": chat_id,
    }

    if account:
        existing_meta = account.metadata_ or {}
        existing_meta.update(folder_ids)
        await repo.update_metadata(account, existing_meta)

    logger.info(f"[GoogleDrive] Folders ensured for user_id={user_id}: {folder_ids}")
    return folder_ids


def upload_file_to_folder(
    service,
    file_content: bytes,
    file_name: str,
    mime_type: str,
    folder_id: str,
) -> dict:
    """
    Upload a file to a specific Google Drive folder.

    Uses MediaIoBaseUpload for in-memory file upload.

    Args:
        service: Google Drive API service instance.
        file_content: Raw file bytes.
        file_name: Name of the file.
        mime_type: MIME type of the file.
        folder_id: Google Drive folder ID to upload into.

    Returns:
        dict with id, name, mimeType, webViewLink.
    """
    file_metadata = {
        "name": file_name,
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_content),
        mimetype=mime_type,
        resumable=True,
    )

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, mimeType, webViewLink",
    ).execute()

    logger.info(f"[GoogleDrive] Uploaded '{file_name}' id={uploaded['id']}")
    return uploaded


def list_files_in_folder(service, folder_id: str, page_size: int = 100) -> list[dict]:
    """
    List all non-trashed files in a specific Google Drive folder.

    Args:
        service: Google Drive API service instance.
        folder_id: Google Drive folder ID.
        page_size: Max files to return.

    Returns:
        List of file metadata dicts.
    """
    query = f"'{folder_id}' in parents and trashed=false"

    results = service.files().list(
        q=query,
        pageSize=page_size,
        fields="files(id, name, mimeType, webViewLink, modifiedTime, size)",
        orderBy="modifiedTime desc",
    ).execute()

    return results.get("files", [])


def download_file(service, file_id: str) -> bytes:
    """
    Download binary content of a Google Drive file.

    Args:
        service: Google Drive API service instance.
        file_id: Google Drive file ID.

    Returns:
        Raw file bytes.
    """
    request = service.files().get_media(fileId=file_id)
    content = request.execute()
    return content


def export_google_doc(service, file_id: str, mime_type: str = "text/plain") -> str:
    """
    Export a Google Docs/Sheets/Slides file to plain text.

    Args:
        service: Google Drive API service instance.
        file_id: Google Drive file ID of a Google Workspace file.
        mime_type: Export format (default: text/plain).

    Returns:
        Exported text content.
    """
    content = service.files().export(fileId=file_id, mimeType=mime_type).execute()
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    return str(content)

