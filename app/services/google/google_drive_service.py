# app/services/google/google_drive_service.py
# Purpose: Google Drive API logic for old testing flow and production DB-backed flow.

import io
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

from app.core.google_config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_TOKEN_URL,
)

from app.core.logger import logger
from app.services.google.google_token_store import get_google_account
from app.services.google.google_client_service import get_drive_client_for_user
from app.repositories.connected_account_repository import ConnectedAccountRepository


# ============================================================
# OLD TESTING FLOW HELPERS
# Used by routes with ?user_id=1
# ============================================================

def get_drive_client(account: dict):
    """
    Old testing helper for in-memory google_token_store flow.

    Used by:
        GET /google/drive/files?user_id=1
        GET /google/drive/search?user_id=1
        GET /google/drive/files/{file_id}?user_id=1
    """
    credentials = Credentials(
        token=account.get("access_token"),
        refresh_token=account.get("refresh_token"),
        token_uri=GOOGLE_TOKEN_URL,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=account.get("scopes", "").split(" ") if account.get("scopes") else [],
    )

    return build("drive", "v3", credentials=credentials)


def list_drive_files(user_id: int, page_size: int = 10) -> dict:
    """
    Old testing route support.
    Uses in-memory google_token_store.
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

        return {
            "files": files,
            "count": len(files),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Google Drive files: {str(e)}",
        )


def search_drive_files(user_id: int, query: str, page_size: int = 10) -> dict:
    """
    Old testing route support.
    Uses in-memory google_token_store.
    """
    account = get_google_account(user_id)
    service = get_drive_client(account)

    try:
        safe_query = query.replace("'", "\\'")
        drive_query = f"name contains '{safe_query}' and trashed=false"

        results = service.files().list(
            q=drive_query,
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime, size)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])

        return {
            "query": query,
            "files": files,
            "count": len(files),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search Google Drive files: {str(e)}",
        )


def get_drive_file_metadata(user_id: int, file_id: str) -> dict:
    """
    Old testing route support.
    Uses in-memory google_token_store.
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Google Drive file metadata: {str(e)}",
        )


# ============================================================
# PRODUCTION DB-BACKED DRIVE LIST / SEARCH / METADATA
# Used by /me routes with JWT current_user
# ============================================================

async def list_drive_files_db(
    user_id: int,
    db: AsyncSession,
    page_size: int = 10,
) -> dict:
    """
    Production DB-backed route.

    Used by:
        GET /google/drive/files/me
    """
    service = await get_drive_client_for_user(user_id=user_id, db=db)

    try:
        results = service.files().list(
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime, size)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])

        return {
            "files": files,
            "count": len(files),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Google Drive files from DB-backed account: {str(e)}",
        )


async def search_drive_files_db(
    user_id: int,
    db: AsyncSession,
    query: str,
    page_size: int = 10,
) -> dict:
    """
    Production DB-backed route.

    Used by:
        GET /google/drive/search/me
    """
    service = await get_drive_client_for_user(user_id=user_id, db=db)

    try:
        safe_query = query.replace("'", "\\'")
        drive_query = f"name contains '{safe_query}' and trashed=false"

        results = service.files().list(
            q=drive_query,
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime, size)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])

        return {
            "query": query,
            "files": files,
            "count": len(files),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search Google Drive files from DB-backed account: {str(e)}",
        )


async def get_drive_file_metadata_db(
    user_id: int,
    db: AsyncSession,
    file_id: str,
) -> dict:
    """
    Production DB-backed route.

    Used by:
        GET /google/drive/files/{file_id}/me
    """
    service = await get_drive_client_for_user(user_id=user_id, db=db)

    try:
        file_metadata = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, webViewLink, modifiedTime, size, owners, createdTime",
        ).execute()

        return file_metadata

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Google Drive file metadata from DB-backed account: {str(e)}",
        )


# ============================================================
# FOLDER CREATION / UPLOAD / DOWNLOAD / EXPORT
# ============================================================

def find_folder_by_name(
    service,
    name: str,
    parent_id: Optional[str] = None,
) -> Optional[str]:
    """
    Find a Google Drive folder by name.

    Returns:
        folder_id if found, otherwise None.
    """
    safe_name = name.replace("'", "\\'")

    query = (
        f"name='{safe_name}' "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )

    if parent_id:
        query += f" and '{parent_id}' in parents"

    try:
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            pageSize=1,
        ).execute()

        files = results.get("files", [])

        if files:
            logger.info(f"[GoogleDrive] Found folder '{name}' id={files[0]['id']}")
            return files[0]["id"]

        return None

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find Google Drive folder '{name}': {str(e)}",
        )


def create_folder(
    service,
    name: str,
    parent_id: Optional[str] = None,
) -> dict:
    """
    Create a Google Drive folder.

    Returns:
        dict with id, name, mimeType, webViewLink.
    """
    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }

    if parent_id:
        file_metadata["parents"] = [parent_id]

    try:
        folder = service.files().create(
            body=file_metadata,
            fields="id, name, mimeType, webViewLink",
        ).execute()

        logger.info(f"[GoogleDrive] Created folder '{name}' id={folder.get('id')}")

        return folder

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Google Drive folder '{name}': {str(e)}",
        )


async def ensure_omnibrain_folders(
    user_id: int,
    db: AsyncSession,
) -> dict:
    """
    Ensure this Google Drive folder structure exists:

    My Drive/
    └── OmniBrain AI/
        ├── Global Documents/
        └── Chat Documents/

    Folder IDs are stored in connected_accounts.metadata.
    """
    repo = ConnectedAccountRepository(db)
    account = await repo.get_by_user_id_and_provider(user_id, "google")


    if not account or not account.access_token:
        raise HTTPException(
            status_code=404,
            detail="Google account not connected. Please login with Google first.",
        )

    metadata = account.metadata_ or {}

    root_folder_id = metadata.get("root_folder_id")
    global_documents_folder_id = metadata.get("global_documents_folder_id")
    chat_documents_folder_id = metadata.get("chat_documents_folder_id")

    if root_folder_id and global_documents_folder_id and chat_documents_folder_id:
        logger.info(f"[GoogleDrive] Folder IDs already cached for user_id={user_id}")

        return {
            "root_folder_id": root_folder_id,
            "global_documents_folder_id": global_documents_folder_id,
            "chat_documents_folder_id": chat_documents_folder_id,
        }

    service = await get_drive_client_for_user(user_id=user_id, db=db)

    # 1. Root folder: OmniBrain AI
    root_folder_id = find_folder_by_name(
        service=service,
        name="OmniBrain AI",
        parent_id=None,
    )

    if not root_folder_id:
        root_folder = create_folder(
            service=service,
            name="OmniBrain AI",
            parent_id=None,
        )
        root_folder_id = root_folder.get("id")

    # 2. Global Documents folder
    global_documents_folder_id = find_folder_by_name(
        service=service,
        name="Global Documents",
        parent_id=root_folder_id,
    )

    if not global_documents_folder_id:
        global_folder = create_folder(
            service=service,
            name="Global Documents",
            parent_id=root_folder_id,
        )
        global_documents_folder_id = global_folder.get("id")

    # 3. Chat Documents folder
    chat_documents_folder_id = find_folder_by_name(
        service=service,
        name="Chat Documents",
        parent_id=root_folder_id,
    )

    if not chat_documents_folder_id:
        chat_folder = create_folder(
            service=service,
            name="Chat Documents",
            parent_id=root_folder_id,
        )
        chat_documents_folder_id = chat_folder.get("id")

    folder_metadata = {
        "root_folder_id": root_folder_id,
        "global_documents_folder_id": global_documents_folder_id,
        "chat_documents_folder_id": chat_documents_folder_id,
    }

    metadata.update(folder_metadata)

    await repo.update_metadata(account, metadata)

    logger.info(f"[GoogleDrive] Folders ensured for user_id={user_id}: {folder_metadata}")

    return folder_metadata

async def search_drive_files_for_user(
    user_id: int,
    db: AsyncSession,
    query: str,
    page_size: int = 50,
) -> dict:
    """
    Search Google Drive files using DB-backed Google connection.
    Used by production JWT route: /google/drive/search/me
    """
    service = await get_drive_client_for_user(user_id, db)

    try:
        drive_query = f"name contains '{query}' and trashed=false"

        results = service.files().list(
            q=drive_query,
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime, size)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])

        return {
            "query": query,
            "files": files,
            "count": len(files),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search Drive files: {str(e)}",
        )
    
async def list_drive_files_for_user(
    user_id: int,
    db: AsyncSession,
    page_size: int = 50,
) -> dict:
    """
    List recent files from Google Drive using DB-backed Google connection.
    Used by production JWT route: /google/drive/files/me
    """
    service = await get_drive_client_for_user(user_id, db)

    try:
        results = service.files().list(
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime, size)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])

        return {
            "files": files,
            "count": len(files),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Drive files: {str(e)}",
        )


def upload_file_to_folder(
    service,
    file_content: bytes,
    file_name: str,
    mime_type: str,
    folder_id: str,
) -> dict:
    """
    Upload a file to a specific Google Drive folder.

    Returns:
        dict with id, name, mimeType, webViewLink.
    """
    if not file_content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    file_metadata = {
        "name": file_name,
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_content),
        mimetype=mime_type or "application/octet-stream",
        resumable=True,
    )

    try:
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, mimeType, webViewLink, modifiedTime, size",
        ).execute()

        logger.info(f"[GoogleDrive] Uploaded file '{file_name}' id={uploaded.get('id')}")

        return uploaded

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file to Google Drive: {str(e)}",
        )


def list_files_in_folder(
    service,
    folder_id: str,
    page_size: int = 100,
) -> list[dict]:
    """
    List non-trashed files inside a specific Google Drive folder.
    """
    query = f"'{folder_id}' in parents and trashed=false"

    try:
        results = service.files().list(
            q=query,
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime, size)",
            orderBy="modifiedTime desc",
        ).execute()

        return results.get("files", [])

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files in Google Drive folder: {str(e)}",
        )


def download_file(
    service,
    file_id: str,
) -> bytes:
    """
    Download binary content of a normal Google Drive file.
    """
    try:
        request = service.files().get_media(fileId=file_id)
        content = request.execute()
        return content

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download Google Drive file: {str(e)}",
        )


def export_google_doc(
    service,
    file_id: str,
    mime_type: str = "text/plain",
) -> str:
    """
    Export Google Docs/Sheets/Slides file to text or another export format.
    """
    try:
        content = service.files().export(
            fileId=file_id,
            mimeType=mime_type,
        ).execute()

        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")

        return str(content)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export Google Workspace file: {str(e)}",
        )