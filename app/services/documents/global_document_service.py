from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.repositories.document_repository import DocumentRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.services.documents.document_upload_service import validate_and_upload_document
from app.services.documents.document_processing_service import extract_text_from_bytes
from app.services.documents.document_chunking_service import chunk_and_embed_text, calculate_checksum
from app.models.document_chunk import DocumentChunk


async def store_global_document_from_drive_file(
    user_id: int,
    file_name: str,
    mime_type: str,
    file_size: int,
    drive_file_id: str,
    drive_web_url: str | None,
    drive_folder_id: str | None,
    content: bytes,
    db: AsyncSession,
    source_type: str = "drive_sync",
):
    doc_repo = DocumentRepository(db)
    existing = await doc_repo.get_by_drive_file_id(user_id, drive_file_id)
    if existing:
        return existing

    text = extract_text_from_bytes(content, mime_type)
    checksum = calculate_checksum(content)

    doc_data = {
        "owner_id": user_id,
        "file_name": file_name,
        "original_file_name": file_name,
        "mime_type": mime_type,
        "file_size": file_size,
        "drive_file_id": drive_file_id,
        "drive_web_url": drive_web_url,
        "drive_folder_id": drive_folder_id,
        "folder_path": "OmniBrain AI/Global Documents",
        "source_type": source_type,
        "processing_status": "completed",
        "chunk_count": 0,
        "checksum": checksum,
    }
    document = await doc_repo.create_document(doc_data)

    chunks_data = await chunk_and_embed_text(text)

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
                embedding=c["embedding"],
            )
        )

    if chunks_to_insert:
        await chunk_repo.bulk_create_chunks(chunks_to_insert)

    await doc_repo.update(document, {"chunk_count": len(chunks_to_insert)})
    return document

async def process_and_store_global_document(user_id: int, file: UploadFile, db: AsyncSession):
    # 1. Upload to Drive
    upload_result = await validate_and_upload_document(user_id, file, "global", db)

    return await store_global_document_from_drive_file(
        user_id=user_id,
        file_name=upload_result["file_name"],
        mime_type=upload_result["mime_type"],
        file_size=upload_result["file_size"],
        drive_file_id=upload_result["drive_file_id"],
        drive_web_url=upload_result["drive_web_url"],
        drive_folder_id=upload_result["drive_folder_id"],
        content=upload_result["content"],
        db=db,
        source_type="upload",
    )
