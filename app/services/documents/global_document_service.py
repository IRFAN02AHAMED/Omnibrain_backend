from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from app.repositories.document_repository import DocumentRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.services.documents.document_upload_service import validate_and_upload_document
from app.services.documents.document_processing_service import extract_text_from_bytes
from app.services.documents.document_chunking_service import chunk_and_embed_text, calculate_checksum
from app.models.document_chunk import DocumentChunk

async def process_and_store_global_document(user_id: int, file: UploadFile, db: AsyncSession):
    # 1. Upload to Drive
    upload_result = await validate_and_upload_document(user_id, file, "global", db)
    
    # 2. Extract Text
    text = extract_text_from_bytes(upload_result["content"], upload_result["mime_type"])
    
    checksum = calculate_checksum(upload_result["content"])
    
    # 3. Create Document DB entry
    doc_repo = DocumentRepository(db)
    doc_data = {
        "owner_id": user_id,
        "file_name": upload_result["file_name"],
        "original_file_name": upload_result["original_file_name"],
        "mime_type": upload_result["mime_type"],
        "file_size": upload_result["file_size"],
        "drive_file_id": upload_result["drive_file_id"],
        "drive_web_url": upload_result["drive_web_url"],
        "drive_folder_id": upload_result["drive_folder_id"],
        "folder_path": "OmniBrain AI/Global Documents",
        "source_type": "upload",
        "processing_status": "completed",
        "chunk_count": 0,
        "checksum": checksum
    }
    document = await doc_repo.create_document(doc_data)
    
    # 4. Chunk and Embed
    chunks_data = await chunk_and_embed_text(text)
    
    # 5. Store chunks
    chunk_repo = DocumentChunkRepository(db)
    chunks_to_insert = []
    for c in chunks_data:
        chunks_to_insert.append(
            DocumentChunk(
                document_id=document.id,
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
