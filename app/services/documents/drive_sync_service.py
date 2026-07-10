from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.sync_log_repository import SyncLogRepository
from app.services.google.google_client_service import get_drive_client_for_user
from app.services.google.google_drive_service import ensure_omnibrain_folders, list_files_in_folder, download_file
from app.services.documents.global_document_service import store_global_document_from_drive_file
from app.repositories.document_repository import DocumentRepository

async def sync_global_documents(user_id: int, db: AsyncSession):
    repo = SyncLogRepository(db)
    log = await repo.create_log(user_id)
    
    try:
        folders = await ensure_omnibrain_folders(user_id, db)
        global_folder_id = folders.get("global_documents_folder_id")
        
        if not global_folder_id:
            raise ValueError("Global documents folder not found")
            
        service = await get_drive_client_for_user(user_id, db)
        files = list_files_in_folder(service, global_folder_id)
        
        results = {
            "files_found": len(files),
            "files_added": 0,
            "files_updated": 0,
            "files_skipped": 0,
            "files_failed": 0
        }
        
        doc_repo = DocumentRepository(db)
        
        for file in files:
            try:
                # Check if file exists in DB by drive_file_id
                existing = await doc_repo.get_by_drive_file_id(user_id, file["id"])
                if existing:
                    # simplistic check for now
                    results["files_skipped"] += 1
                    continue
                    
                # Download and process
                content = download_file(service, file["id"])

                await store_global_document_from_drive_file(
                    user_id=user_id,
                    file_name=file["name"],
                    mime_type=file.get("mimeType", "application/octet-stream"),
                    file_size=int(file.get("size") or len(content)),
                    drive_file_id=file["id"],
                    drive_web_url=file.get("webViewLink"),
                    drive_folder_id=global_folder_id,
                    content=content,
                    db=db,
                    source_type="drive_sync",
                )
                results["files_added"] += 1
                
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Sync error for file {file.get('name')}: {e}")
                results["files_failed"] += 1
                
        await repo.update_result(log, "completed", results)
        return {"status": "completed", "results": results}
        
    except Exception as e:
        await repo.update_result(log, "failed", {}, error_message=str(e))
        raise
