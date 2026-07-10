from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from app.repositories.session_document_repository import SessionDocumentRepository
from app.repositories.session_document_chunk_repository import SessionDocumentChunkRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.services.documents.document_upload_service import validate_and_upload_document
from app.services.documents.document_processing_service import extract_text_from_bytes
from app.services.documents.document_chunking_service import chunk_and_embed_text
from app.models.session_document_chunk import SessionDocumentChunk

async def process_and_store_session_document(session_id: int, user_id: int, file: UploadFile, db: AsyncSession):
    # Verify session ownership
    session_repo = ChatSessionRepository(db)
    session = await session_repo.get_by_id_and_user(session_id, user_id)
    if not session:
        raise ValueError("Session not found")
        
    # 1. Upload to Drive (using chat folder)
    upload_result = await validate_and_upload_document(user_id, file, "chat", db)
    
    # 2. Extract Text
    text = extract_text_from_bytes(upload_result["content"], upload_result["mime_type"])
    
    # 3. Create Document DB entry
    doc_repo = SessionDocumentRepository(db)
    doc_data = {
        "session_id": session_id,
        "owner_id": user_id,
        "file_name": upload_result["file_name"],
        "original_file_name": upload_result["original_file_name"],
        "mime_type": upload_result["mime_type"],
        "file_size": upload_result["file_size"],
        "drive_file_id": upload_result["drive_file_id"],
        "drive_web_url": upload_result["drive_web_url"],
        "drive_folder_id": upload_result["drive_folder_id"],
        "folder_path": "OmniBrain AI/Chat Documents",
        "processing_status": "completed",
        "chunk_count": 0
    }
    document = await doc_repo.create_session_document(doc_data)
    
    # 4. Chunk and Embed
    chunks_data = await chunk_and_embed_text(text)
    
    # 5. Store chunks
    chunk_repo = SessionDocumentChunkRepository(db)
    chunks_to_insert = []
    for c in chunks_data:
        chunks_to_insert.append(
            SessionDocumentChunk(
                session_document_id=document.id,
                session_id=session_id,
                owner_id=user_id,
                chunk_index=c["chunk_index"],
                chunk_text=c["chunk_text"],
                token_count=c["token_count"],
                embedding=c["embedding"]
            )
        )
    if chunks_to_insert:
        await chunk_repo.bulk_create_chunks(chunks_to_insert)
    
    # Update chunk count
    await doc_repo.update(document, {"chunk_count": len(chunks_to_insert)})
    
    return document
