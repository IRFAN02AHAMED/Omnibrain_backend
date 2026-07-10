import mimetypes
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.google.google_client_service import get_drive_client_for_user
from app.services.google.google_drive_service import ensure_omnibrain_folders, upload_file_to_folder

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB

async def validate_and_upload_document(user_id: int, file: UploadFile, folder_type: str, db: AsyncSession) -> dict:
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {file_ext}")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    folders = await ensure_omnibrain_folders(user_id, db)
    folder_id = folders.get("global_documents_folder_id") if folder_type == "global" else folders.get("chat_documents_folder_id")
    
    if not folder_id:
        raise HTTPException(status_code=500, detail="Could not determine Drive folder ID")
        
    mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    service = await get_drive_client_for_user(user_id, db)
    uploaded = upload_file_to_folder(service, content, file.filename, mime_type, folder_id)
    
    return {
        "file_name": file.filename,
        "original_file_name": file.filename,
        "mime_type": mime_type,
        "file_size": len(content),
        "drive_file_id": uploaded.get("id"),
        "drive_web_url": uploaded.get("webViewLink"),
        "drive_folder_id": folder_id,
        "content": content
    }
