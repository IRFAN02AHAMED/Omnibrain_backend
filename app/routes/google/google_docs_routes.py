# app/routes/google/google_docs_routes.py
# Purpose: Google Docs API routes for listing and reading documents.

from fastapi import APIRouter, Query

from app.services.google.google_docs_service import (
    list_google_docs,
    read_google_doc,
)

# TODO: Replace `user_id` query parameter with current logged-in user from JWT dependency later.

router = APIRouter(prefix="/google/docs", tags=["Google Docs"])


@router.get("/files")
async def docs_files(
    user_id: int = Query(..., description="User ID"),
    page_size: int = Query(10, description="Number of documents to return"),
):
    """
    List Google Docs from Drive.

    Returns documents filtered by Google Docs MIME type,
    ordered by most recently modified.

    Example:
        GET /google/docs/files?user_id=1&page_size=10
    """
    return list_google_docs(user_id=user_id, page_size=page_size)


@router.get("/{document_id}")
async def docs_read(
    document_id: str,
    user_id: int = Query(..., description="User ID"),
):
    """
    Read the content of a specific Google Doc.

    Returns document_id, title, and extracted plain text content.

    Example:
        GET /google/docs/DOCUMENT_ID?user_id=1
    """
    return read_google_doc(user_id=user_id, document_id=document_id)
