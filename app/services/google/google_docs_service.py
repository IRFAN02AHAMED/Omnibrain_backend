# app/services/google/google_docs_service.py
# Purpose: Google Docs API logic for listing and reading documents.

from fastapi import HTTPException

from app.services.google.google_token_store import get_google_account
from app.services.google.google_client_service import get_drive_client, get_docs_client
from app.services.google.google_helper_service import extract_google_doc_text


def list_google_docs(user_id: int, page_size: int = 10) -> dict:
    """
    List Google Docs from the user's Drive.

    Uses the Drive API to filter files by Google Docs MIME type.
    Returns id, name, mimeType, webViewLink, and modifiedTime.

    Args:
        user_id: The application user ID.
        page_size: Number of documents to return (default: 10).

    Returns:
        dict: Dictionary with 'documents' list and 'count'.
    """
    account = get_google_account(user_id)
    service = get_drive_client(account)

    try:
        drive_query = "mimeType='application/vnd.google-apps.document' and trashed=false"

        results = service.files().list(
            q=drive_query,
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, modifiedTime)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        return {"documents": files, "count": len(files)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Google Docs: {str(e)}")


def read_google_doc(user_id: int, document_id: str) -> dict:
    """
    Read the content of a specific Google Doc.

    Uses the Docs API to fetch the full document and then extracts
    plain text using extract_google_doc_text().

    Args:
        user_id: The application user ID.
        document_id: The Google Docs document ID.

    Returns:
        dict: Dictionary with document_id, title, and extracted text content.
    """
    account = get_google_account(user_id)
    service = get_docs_client(account)

    try:
        document = service.documents().get(documentId=document_id).execute()

        title = document.get("title", "Untitled")
        text = extract_google_doc_text(document)

        return {
            "document_id": document_id,
            "title": title,
            "text": text,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read Google Doc: {str(e)}")
